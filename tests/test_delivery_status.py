"""P5 controller accepts only real P3 receipts bound to source and candidate SHA."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from agentic.candidate_intake import verify_and_stage_candidate
from agentic.delivery_status import ROUNDS, evaluate_delivery_rounds


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_dir(root: Path) -> Path:
    original = root / "source"
    (original / "contracts").mkdir(parents=True)
    for name, data in (
        ("sales.csv", b"original,rows\n1,2\n"),
        ("test_virtual_column.py", b"def test_original(): assert True\n"),
        ("contracts/data_policy.json", b'{"version":1}\n'),
    ):
        (original / name).write_bytes(data)
    return original


def round_artifacts(root: Path, original: Path, number: int, status: str,
                    previous_files: dict | None = None, prior_raw: bytes = b""):
    candidate_label, sandbox_label = ROUNDS[number - 1]
    candidate = root / candidate_label
    sandbox = root / sandbox_label
    candidate.mkdir(parents=True)
    sandbox.mkdir(parents=True)
    files = {
        "solution.py": f"def f():\n    return {number}\n".encode(),
        "pipeline.py": f"def main():\n    return {number}\n".encode(),
        "README.md": f"Candidate round {number}\n".encode(),
        "tests/test_case.py": b"def test_x():\n    assert True\n",
    }
    with zipfile.ZipFile(candidate / "candidate_bundle.zip", "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    manifest = [{"path": name, "sha256": digest(data)} for name, data in files.items()]
    inputs = {
        name: digest((original / name).read_bytes())
        for name in ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json")
    }
    gate = {"status": "CANDIDATE_READY_FOR_SANDBOX",
            "failures": [], "actual_written_files": manifest}
    request = {"status": "PENDING_SANDBOX_VALIDATION",
               "files": manifest, "protected_hashes": inputs}
    (candidate / "engineer_gate.json").write_text(json.dumps(gate), encoding="utf-8")
    (candidate / "validation_request.json").write_text(json.dumps(request), encoding="utf-8")
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix="p5-test-admission-") as temporary:
        receipt = verify_and_stage_candidate(
            archive_path=candidate / "candidate_bundle.zip",
            engineer_gate=gate, validation_request=request,
            original_checkout=original, destination=Path(temporary) / "candidate",
        )
    (sandbox / "admission.json").write_text(json.dumps(receipt), encoding="utf-8")
    if number > 1:
        previous_files = previous_files or {}
        current = {f["path"]: f["sha256"] for f in manifest}
        lineage = {
            "iteration": number, "previous_file_hashes": previous_files,
            "current_file_hashes": current, "actual_change": previous_files != current,
            "previous_p3_verdict_sha256": digest(prior_raw),
        }
        (candidate / "rework_lineage.json").write_text(json.dumps(lineage), encoding="utf-8")
    result = {
        "schema_version": 1, "source": "independent_p3_stdlib_oracle",
        "status": status,
    }
    if status == "PASSED":
        result.update({
            "reconciliation": "passed", "sandbox_test_exit_code": 0,
            "sandbox_pipeline_exit_code": 0, "regions": {
                "Central": "1.00", "East": "2.00", "North": "3.00",
                "South": "4.00", "West": "5.00",
            },
            "source_sha256": inputs["sales.csv"],
        })
    else:
        result["failure"] = "Independent failing pytest assertions"
    raw = json.dumps(result).encode()
    (sandbox / "verification.json").write_bytes(raw)
    return {f["path"]: f["sha256"] for f in manifest}, raw


def evaluate(tmp_path: Path, root: Path, original: Path):
    return evaluate_delivery_rounds(root, original, tmp_path / "stages")


def test_first_candidate_pass_still_requires_verifier(tmp_path: Path):
    original = source_dir(tmp_path)
    artifacts = tmp_path / "artifacts"
    round_artifacts(artifacts, original, 1, "PASSED")
    result = evaluate(tmp_path, artifacts, original)
    assert result["status"] == "WAITING_VERIFIER"
    assert result["accepted_for_verification_iteration"] == 1
    assert result["approval"] == "NOT_APPROVED_FOR_PR_OR_MERGE"


def test_second_round_can_pass_only_with_provenance(tmp_path: Path):
    original = source_dir(tmp_path)
    artifacts = tmp_path / "artifacts"
    old, raw = round_artifacts(artifacts, original, 1, "FAILED")
    round_artifacts(artifacts, original, 2, "PASSED", old, raw)
    result = evaluate(tmp_path, artifacts, original)
    assert result["status"] == "WAITING_VERIFIER"
    assert result["accepted_for_verification_iteration"] == 2
    assert result["iterations_used"] == 2
    assert result["history"][0]["candidate_status"] == "FAILED"


def test_three_genuine_failures_are_rejected(tmp_path: Path):
    original = source_dir(tmp_path)
    artifacts = tmp_path / "artifacts"
    old, raw = round_artifacts(artifacts, original, 1, "FAILED")
    old, raw = round_artifacts(artifacts, original, 2, "FAILED", old, raw)
    round_artifacts(artifacts, original, 3, "FAILED", old, raw)
    result = evaluate(tmp_path, artifacts, original)
    assert result["status"] == "REJECTED"
    assert result["iterations_used"] == 3
    assert result["accepted_for_verification_iteration"] is None


def test_missing_rework_evidence_cannot_fake_pass(tmp_path: Path):
    original = source_dir(tmp_path)
    artifacts = tmp_path / "artifacts"
    round_artifacts(artifacts, original, 1, "FAILED")
    result = evaluate(tmp_path, artifacts, original)
    assert result["status"] == "INCOMPLETE"
    assert result["accepted_for_verification_iteration"] is None


def test_forged_rework_lineage_is_rejected(tmp_path: Path):
    original = source_dir(tmp_path)
    artifacts = tmp_path / "artifacts"
    old, raw = round_artifacts(artifacts, original, 1, "FAILED")
    round_artifacts(artifacts, original, 2, "PASSED", old, raw)
    path = artifacts / ROUNDS[1][0] / "rework_lineage.json"
    lineage = json.loads(path.read_text())
    lineage["previous_p3_verdict_sha256"] = "0" * 64
    path.write_text(json.dumps(lineage), encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        evaluate(tmp_path, artifacts, original)


def test_forged_source_hash_is_rejected(tmp_path: Path):
    original = source_dir(tmp_path)
    artifacts = tmp_path / "artifacts"
    round_artifacts(artifacts, original, 1, "PASSED")
    path = artifacts / ROUNDS[0][1] / "verification.json"
    x = json.loads(path.read_text())
    x["source_sha256"] = "0" * 64
    path.write_text(json.dumps(x), encoding="utf-8")
    with pytest.raises(ValueError, match="False P3 PASS"):
        evaluate(tmp_path, artifacts, original)


def test_operator_bound_one_failure_is_rejected_not_incomplete(tmp_path: Path):
    original = source_dir(tmp_path)
    artifacts = tmp_path / "artifacts"
    round_artifacts(artifacts, original, 1, "FAILED")
    result = evaluate_delivery_rounds(
        artifacts, original, tmp_path / "stages", max_rounds=1,
    )
    assert result["status"] == "REJECTED"
    assert result["iterations_used"] == 1
    assert result["max_iterations"] == 1


def test_operator_bound_two_failures_are_rejected(tmp_path: Path):
    original = source_dir(tmp_path)
    artifacts = tmp_path / "artifacts"
    old, raw = round_artifacts(artifacts, original, 1, "FAILED")
    round_artifacts(artifacts, original, 2, "FAILED", old, raw)
    result = evaluate_delivery_rounds(
        artifacts, original, tmp_path / "stages", max_rounds=2,
    )
    assert result["status"] == "REJECTED"
    assert result["iterations_used"] == 2


@pytest.mark.parametrize("bad_limit", [0, 4, -1])
def test_invalid_attempt_budget_rejected(tmp_path: Path, bad_limit: int):
    original = source_dir(tmp_path)
    with pytest.raises(ValueError, match="max_rounds"):
        evaluate_delivery_rounds(
            tmp_path / "none", original, tmp_path / "stages",
            max_rounds=bad_limit,
        )
