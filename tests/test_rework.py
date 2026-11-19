"""P5: a failed sandbox must lead to a genuine changed candidate or STOP."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from agentic.engineer_gate import EngineerLedger, REQUIRED_CALLS
from agentic.rework import (
    ReworkInputError, ReworkLedger, evaluate_rework, verified_failed_candidate,
)
from agentic.schemas.engineer import CandidateFileEvidence, EngineerReport
from agentic.workspace import create_workspace


ARCHITECT_DIGEST = "a" * 64
REQS = [
    "virtual_column", "invalid_expressions", "source_cleaning",
    "revenue_formula", "regional_aggregation", "tests_and_readme",
]


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def original_fixture(tmp: Path) -> Path:
    root = tmp / "source"
    (root / "contracts").mkdir(parents=True)
    (root / "sales.csv").write_text("original,values\n1,2\n", encoding="utf-8")
    (root / "test_virtual_column.py").write_text("def test_base(): pass\n", encoding="utf-8")
    (root / "contracts/data_policy.json").write_text('{"version":1}\n', encoding="utf-8")
    return root


def candidate_fixture(tmp: Path):
    source = original_fixture(tmp)
    original = tmp / "old-engineer"
    original.mkdir()
    code = {
        "solution.py": b"def f():\n    return 1\n",
        "pipeline.py": b"def main():\n    return 0\n",
        "README.md": b"Model-written original candidate\n",
        "tests/test_generated.py": b"def test_x():\n    assert True\n",
    }
    with zipfile.ZipFile(original / "candidate_bundle.zip", "w") as archive:
        for name, body in code.items():
            archive.writestr(name, body)
    files = [{"path": name, "sha256": _sha(body)} for name, body in code.items()]
    protected = {
        name: _sha((source / name).read_bytes())
        for name in ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json")
    }
    (original / "engineer_gate.json").write_text(
        json.dumps({"status": "CANDIDATE_READY_FOR_SANDBOX",
                    "failures": [], "actual_written_files": files}),
        encoding="utf-8",
    )
    (original / "validation_request.json").write_text(
        json.dumps({"status": "PENDING_SANDBOX_VALIDATION",
                    "protected_hashes": protected, "files": files}),
        encoding="utf-8",
    )
    failures = tmp / "p3"
    failures.mkdir()
    (failures / "test_exit_code.txt").write_text("1", encoding="utf-8")
    (failures / "pipeline_exit_code.txt").write_text("98", encoding="utf-8")
    (failures / "tests.log").write_text("FAILED employer whitespace test", encoding="utf-8")
    (failures / "pipeline.log").write_text("Skipped because original pytest failed", encoding="utf-8")
    (failures / "verification.json").write_text(
        json.dumps({"status": "FAILED", "source": "independent_p3_stdlib_oracle",
                    "sandbox_test_exit_code": 1, "sandbox_pipeline_exit_code": 98,
                    "failure": "Sandbox test suite or candidate pipeline exited nonzero"}),
        encoding="utf-8",
    )
    # The trusted admission must be exactly what P3 independently computed.
    from agentic.candidate_intake import verify_and_stage_candidate
    admission = verify_and_stage_candidate(
        archive_path=original / "candidate_bundle.zip",
        engineer_gate=json.loads((original / "engineer_gate.json").read_text()),
        validation_request=json.loads((original / "validation_request.json").read_text()),
        original_checkout=source, destination=tmp / "first-stage",
    )
    (failures / "admission.json").write_text(json.dumps(admission), encoding="utf-8")
    return source, original, failures, files


def test_real_failed_candidate_stage_has_verified_lineage(tmp_path: Path, monkeypatch):
    source, previous, failures, files = candidate_fixture(tmp_path)
    monkeypatch.setattr("agentic.rework.ROOT", source)
    verdict, _, staged, digest = verified_failed_candidate(
        previous_dir=previous, p3_dir=failures, stage=tmp_path / "rework-stage",
    )
    assert verdict["status"] == "FAILED"
    assert staged["candidate_count"] == 4
    assert {f["path"] for f in staged["files"]} == {f["path"] for f in files}
    assert len(digest) == 64
    assert (tmp_path / "rework-stage/solution.py").is_file()


def test_missing_sandbox_evidence_is_infrastructure_error(tmp_path: Path, monkeypatch):
    source, previous, failures, _ = candidate_fixture(tmp_path)
    monkeypatch.setattr("agentic.rework.ROOT", source)
    (failures / "test_exit_code.txt").unlink()
    with pytest.raises(ReworkInputError, match="INFRA_FAILURE"):
        verified_failed_candidate(
            previous_dir=previous, p3_dir=failures, stage=tmp_path / "rework-stage",
        )


def test_fake_p3_success_must_not_trigger_rework(tmp_path: Path, monkeypatch):
    source, previous, failures, _ = candidate_fixture(tmp_path)
    monkeypatch.setattr("agentic.rework.ROOT", source)
    (failures / "verification.json").write_text(
        json.dumps({"status": "PASSED", "source": "independent_p3_stdlib_oracle"}),
        encoding="utf-8",
    )
    with pytest.raises(ReworkInputError, match="not FAILED"):
        verified_failed_candidate(
            previous_dir=previous, p3_dir=failures, stage=tmp_path / "rework-stage",
        )


def new_candidate(tmp_path: Path):
    source = original_fixture(tmp_path)
    ws = create_workspace(source, tmp_path / "candidate", "rebuild")
    ws.write_file("solution.py", "def f():\n    return 2\n")
    ws.write_file("pipeline.py", "def main():\n    return 0\n")
    ws.write_file("README.md", "Written candidate after genuine failure.")
    ws.write_file("tests/test_generated.py", "def test_x():\n    assert True\n")
    ws.request_validation("Independent isolated execution of corrected candidate requested")
    files = ws.validation_requests[-1]["files"]
    report = EngineerReport(
        role="data_engineer", mode="rebuild", architect_report_sha256=ARCHITECT_DIGEST,
        summary="Actual code files corrected after earlier validation failed.",
        actual_files_written=[
            CandidateFileEvidence(
                path=item["path"], sha256=item["sha256"], requirement_keys=REQS,
            ) for item in files
        ],
        validation_requested=True,
    )
    ledger = EngineerLedger()
    for tool in sorted(REQUIRED_CALLS):
        ledger.record(tool)
    for name in ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json"):
        ledger.record("read_workspace_file", name)
    return ws, report, ledger


def test_rework_pass_requires_actual_feedback_and_previous_code_reads(tmp_path: Path):
    ws, report, ledger = new_candidate(tmp_path)
    old = {item["path"]: "0" * 64 for item in ws.validation_requests[-1]["files"]}
    record = ReworkLedger(read_failure=True, previous_reads={"solution.py", "pipeline.py"})
    gate, lineage = evaluate_rework(
        report=report, workspace=ws, engineer_ledger=ledger,
        rework_ledger=record, architect_digest=ARCHITECT_DIGEST,
        previous_file_hashes=old,
    )
    assert gate["status"] == "CANDIDATE_READY_FOR_SANDBOX"
    assert not gate["failures"]
    assert lineage["actual_change"]


def test_rework_without_reading_failure_is_rejected(tmp_path: Path):
    ws, report, ledger = new_candidate(tmp_path)
    gate, _ = evaluate_rework(
        report=report, workspace=ws, engineer_ledger=ledger,
        rework_ledger=ReworkLedger(previous_reads={"solution.py", "pipeline.py"}),
        architect_digest=ARCHITECT_DIGEST,
        previous_file_hashes={"solution.py": "0" * 64},
    )
    assert gate["status"] == "INCOMPLETE"
    assert any("never read" in x for x in gate["failures"])


def test_identical_rework_candidate_cannot_pass(tmp_path: Path):
    ws, report, ledger = new_candidate(tmp_path)
    same = {entry["path"]: entry["sha256"] for entry in ws.validation_requests[-1]["files"]}
    gate, _ = evaluate_rework(
        report=report, workspace=ws, engineer_ledger=ledger,
        rework_ledger=ReworkLedger(read_failure=True, previous_reads={"solution.py", "pipeline.py"}),
        architect_digest=ARCHITECT_DIGEST, previous_file_hashes=same,
    )
    assert gate["status"] == "INCOMPLETE"
    assert any("identical" in x for x in gate["failures"])
