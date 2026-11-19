"""P6 publisher must fail closed on missing P4 real proof or mismatched SHA."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from pipeline import ROOT
from agentic.publisher_prepare import DraftPublicationError, prepare_publication
from agentic.verifier_gate import TEST_PATH, candidate_manifest_digest, validate_adversarial_test


RUN = "123456"
BASE = "a" * 40
VERIFIER_TEST = (
    "import pandas as pd\nfrom solution import add_virtual_column\n\n"
    "def test_math_after_real_source_review():\n"
    "    value = pd.DataFrame({'a': [2], 'b': [3]})\n"
    "    assert add_virtual_column(value, 'a + b', 'total').at[0,'total'] == 5\n"
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fixture(tmp: Path) -> Path:
    collection = tmp / "evidence"
    for name in (
        "p2-engineer-candidate-pending-sandbox",
        "p3-independent-sandbox-validation",
        "p5-bounded-run-state",
        "p4-independent-adversarial-validation",
        "p4-verifier-evidence/tests",
    ):
        (collection / name).mkdir(parents=True)
    source = collection / "p2-engineer-candidate-pending-sandbox"
    code = {
        "solution.py": b"def add_virtual_column(df, role, name):\n    return df\n",
        "pipeline.py": b"def main():\n    return 1\n",
        "README.md": b"Independent candidate, requires human review.\n",
        "tests/test_engineer.py": b"def test_simple():\n    assert 1 + 2 == 3\n",
    }
    with zipfile.ZipFile(source / "candidate_bundle.zip", "w") as archive:
        for path, body in code.items():
            archive.writestr(path, body)
    files = [{"path": path, "sha256": sha(body)} for path, body in code.items()]
    protected = {
        name: sha((ROOT / name).read_bytes())
        for name in ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json")
    }
    (source / "engineer_gate.json").write_text(json.dumps({
        "status": "CANDIDATE_READY_FOR_SANDBOX", "failures": [],
        "actual_written_files": files,
    }))
    (source / "validation_request.json").write_text(json.dumps({
        "status": "PENDING_SANDBOX_VALIDATION", "files": files,
        "protected_hashes": protected,
    }))
    candidate_digest = candidate_manifest_digest(files)
    receipt = collection / "p3-independent-sandbox-validation/verification.json"
    receipt.write_text(json.dumps({
        "status": "PASSED", "reconciliation": "passed",
        "source_sha256": protected["sales.csv"],
    }))
    (collection / "p5-bounded-run-state/run_state.json").write_text(json.dumps({
        "status": "WAITING_VERIFIER", "github_run_id": RUN,
        "base_commit_sha": BASE, "accepted_for_verification_iteration": 1,
    }))
    p4_dir = collection / "p4-independent-adversarial-validation"
    verifier_sha = validate_adversarial_test(VERIFIER_TEST)
    (collection / "p4-verifier-evidence" / TEST_PATH).write_text(VERIFIER_TEST)
    (p4_dir / "admission.json").write_text(json.dumps({
        "candidate_manifest_sha256": candidate_digest,
        "original_test_sha256": protected["test_virtual_column.py"],
        "verifier_test_sha256": verifier_sha,
    }))
    output_csv = (ROOT / "revenue_by_region.csv").read_bytes()
    (p4_dir / "revenue_by_region.csv").write_bytes(output_csv)
    good_oracle = json.dumps({
        "status": "PASSED", "reconciliation": "passed",
        "sandbox_test_exit_code": 0, "sandbox_pipeline_exit_code": 0,
        "output_sha256": sha(output_csv), "net_revenue": "2570247.03",
    }).encode()
    (p4_dir / "positive_finance_oracle.json").write_bytes(good_oracle)
    (p4_dir / "verifier_verdict.json").write_text(json.dumps({
        "status": "PASSED", "next_stage": "P6_DRAFT_PR_REVIEW",
        "falsification_sensitivity": "PASSED",
        "positive_test_exit_code": 0, "positive_pipeline_exit_code": 0,
        "negative_mutation_test_exit_code": 1, "iteration": 1, "failures": [],
        "candidate_manifest_sha256": candidate_digest,
        "verifier_test_sha256": verifier_sha,
        "positive_oracle_sha256": sha(good_oracle),
    }))
    return collection


def publish(tmp_path: Path, evidence: Path):
    return prepare_publication(
        artifacts=evidence, original=ROOT,
        destination=tmp_path / "staged", run_id=RUN, base_sha=BASE,
    )


def test_only_genuine_verified_source_is_staged_for_human_review(tmp_path: Path):
    evidence = fixture(tmp_path)
    result = publish(tmp_path, evidence)
    assert result["status"] == "HUMAN_REVIEW_REQUIRED"
    assert result["candidate_ci_status"] == "NOT_YET_RUN"
    assert result["verified_net_revenue"] == "2570247.03"
    assert result["p4_independent_verifier_status"] == "PASSED"
    assert result["approval"] == "NO_AGENT_POLICY_APPROVAL_OR_AUTOMERGE"
    assert (tmp_path / "staged/revenue_by_region.csv").read_bytes() == (ROOT / "revenue_by_region.csv").read_bytes()
    assert (tmp_path / "staged" / TEST_PATH).read_text() == VERIFIER_TEST
    assert (tmp_path / "staged/reports/agentic_delivery_manifest.json").is_file()
    assert "human review" in (tmp_path / "staged/draft-pr-body.md").read_text().lower()


def test_missing_p4_verdict_prohibits_draft(tmp_path: Path):
    evidence = fixture(tmp_path)
    (evidence / "p4-independent-adversarial-validation/verifier_verdict.json").unlink()
    with pytest.raises(DraftPublicationError, match="Missing"):
        publish(tmp_path, evidence)


@pytest.mark.parametrize("bad_status", ["WEAK_VERIFIER_TEST", "REWORK_REQUIRED", "INCOMPLETE"])
def test_unverified_or_weak_verifier_never_publishes(tmp_path: Path, bad_status: str):
    evidence = fixture(tmp_path)
    file = evidence / "p4-independent-adversarial-validation/verifier_verdict.json"
    obj = json.loads(file.read_text())
    obj["status"] = bad_status
    file.write_text(json.dumps(obj))
    with pytest.raises(DraftPublicationError, match="did not pass"):
        publish(tmp_path, evidence)


def test_modified_financial_output_without_oracle_sha_is_rejected(tmp_path: Path):
    evidence = fixture(tmp_path)
    (evidence / "p4-independent-adversarial-validation/revenue_by_region.csv").write_text(
        "region,revenue\nCentral,999999.99\n", encoding="utf-8"
    )
    with pytest.raises(DraftPublicationError, match="not identical"):
        publish(tmp_path, evidence)


def test_different_run_and_git_sha_cannot_be_published(tmp_path: Path):
    evidence = fixture(tmp_path)
    with pytest.raises(DraftPublicationError, match="source run ID or SHA"):
        prepare_publication(
            artifacts=evidence, original=ROOT, destination=tmp_path / "staged",
            run_id="444444", base_sha=BASE,
        )


def test_forged_verifier_test_sha_blocks_publication(tmp_path: Path):
    evidence = fixture(tmp_path)
    test = evidence / "p4-verifier-evidence" / TEST_PATH
    test.write_text(VERIFIER_TEST.replace("== 5", "== 7"), encoding="utf-8")
    with pytest.raises(DraftPublicationError, match="Verifier test SHA mismatch"):
        publish(tmp_path, evidence)
