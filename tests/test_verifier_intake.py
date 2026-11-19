"""P4: untrusted Verifier test bytes cannot bypass model and candidate SHA gates."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from agentic.candidate_intake import verify_and_stage_candidate
from agentic.verifier_gate import (
    REQUIRED_TOOLS, TEST_PATH, candidate_manifest_digest,
    validate_adversarial_test,
)
from agentic.verifier_intake import VerifierAdmissionError, stage_adversarial_test


ADVERSARIAL_TEST = (
    "import pandas as pd\n"
    "from solution import add_virtual_column\n\n"
    "def test_math_correct():\n"
    "    df = pd.DataFrame({'a': [2], 'b': [3]})\n"
    "    assert add_virtual_column(df, 'a + b', 'total').at[0, 'total'] == 5\n"
)


def prepare(tmp_path: Path):
    source = tmp_path / "original"
    (source / "contracts").mkdir(parents=True)
    for name, raw in (
        ("sales.csv", b"x,y\n1,2\n"),
        ("test_virtual_column.py", b"def test_x(): assert True\n"),
        ("contracts/data_policy.json", b'{"version":1}\n'),
    ):
        (source / name).write_bytes(raw)
    evidence = tmp_path / "collected"
    candidate = evidence / "p2-engineer-candidate-pending-sandbox"
    sandbox = evidence / "p3-independent-sandbox-validation"
    verifier = evidence / "p4-verifier-evidence"
    state = evidence / "p5-bounded-run-state"
    for folder in (candidate, sandbox, verifier / "tests", state):
        folder.mkdir(parents=True)
    files = {"solution.py": b"def f(): return 1\n",
             "pipeline.py": b"def main(): return 2\n"}
    with zipfile.ZipFile(candidate / "candidate_bundle.zip", "w") as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    manifest = [{"path": name, "sha256": hashlib.sha256(raw).hexdigest()}
                for name, raw in files.items()]
    policy = {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json")
    }
    gate = {"status": "CANDIDATE_READY_FOR_SANDBOX",
            "failures": [], "actual_written_files": manifest}
    request = {"status": "PENDING_SANDBOX_VALIDATION",
               "protected_hashes": policy, "files": manifest}
    (candidate / "engineer_gate.json").write_text(json.dumps(gate))
    (candidate / "validation_request.json").write_text(json.dumps(request))
    admitted = verify_and_stage_candidate(
        archive_path=candidate / "candidate_bundle.zip",
        engineer_gate=gate, validation_request=request,
        original_checkout=source, destination=tmp_path / "trusted-staging",
    )
    (sandbox / "admission.json").write_text(json.dumps(admitted))
    p3_result = {"status": "PASSED", "reconciliation": "passed",
                 "source": "independent_p3_stdlib_oracle"}
    p3_bytes = json.dumps(p3_result).encode()
    (sandbox / "verification.json").write_bytes(p3_bytes)
    (state / "run_state.json").write_text(json.dumps({
        "status": "WAITING_VERIFIER",
        "accepted_for_verification_iteration": 1,
    }))
    candidate_sha = candidate_manifest_digest(admitted["files"])
    test_sha = validate_adversarial_test(ADVERSARIAL_TEST)
    (verifier / TEST_PATH).write_text(ADVERSARIAL_TEST)
    (verifier / "verifier_gate.json").write_text(json.dumps({
        "status": "PENDING_ADVERSARIAL_EXECUTION",
        "failures": [], "verified_tool_calls": list(REQUIRED_TOOLS),
        "candidate_manifest_sha256": candidate_sha,
        "proposed_test_sha256": test_sha,
    }))
    (verifier / "verifier_report.json").write_text(json.dumps({
        "candidate_manifest_sha256": candidate_sha,
        "p3_receipt_sha256": hashlib.sha256(p3_bytes).hexdigest(),
        "original_test_sha256": policy["test_virtual_column.py"],
        "proposed_test_sha256": test_sha,
        "next_action": "request_independent_test",
    }))
    return source, evidence


def test_real_verifier_test_is_staged_only_after_provenance(tmp_path: Path):
    original, evidence = prepare(tmp_path)
    result = stage_adversarial_test(
        artifacts=evidence, original=original, destination=tmp_path / "verifier-stage",
    )
    assert result["status"] == "ADMITTED_FOR_INDEPENDENT_ADVERSARIAL_TEST"
    assert result["iteration"] == 1
    assert (tmp_path / "verifier-stage" / TEST_PATH).read_text() == ADVERSARIAL_TEST


def test_wrong_test_sha_is_not_admitted(tmp_path: Path):
    original, evidence = prepare(tmp_path)
    path = evidence / "p4-verifier-evidence/verifier_gate.json"
    value = json.loads(path.read_text())
    value["proposed_test_sha256"] = "f" * 64
    path.write_text(json.dumps(value))
    with pytest.raises(VerifierAdmissionError, match="SHA"):
        stage_adversarial_test(
            artifacts=evidence, original=original, destination=tmp_path / "verifier-stage",
        )


def test_forged_p3_receipt_blocks_verifier(tmp_path: Path):
    original, evidence = prepare(tmp_path)
    (evidence / "p3-independent-sandbox-validation/verification.json").write_text(
        '{"status":"FAILED"}'
    )
    with pytest.raises(VerifierAdmissionError, match="P3"):
        stage_adversarial_test(
            artifacts=evidence, original=original, destination=tmp_path / "verifier-stage",
        )


def test_unapproved_p5_candidate_blocks_verifier(tmp_path: Path):
    original, evidence = prepare(tmp_path)
    state = evidence / "p5-bounded-run-state/run_state.json"
    state.write_text('{"status":"REJECTED","accepted_for_verification_iteration":null}')
    with pytest.raises(VerifierAdmissionError, match="No P5"):
        stage_adversarial_test(
            artifacts=evidence, original=original, destination=tmp_path / "verifier-stage",
        )
