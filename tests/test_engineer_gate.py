"""P2 Engineer hard gate: a JSON success claim without real file writes is invalid."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic.engineer_gate import EngineerLedger, REQUIRED_CALLS, evaluate_engineer
from agentic.schemas.engineer import CandidateFileEvidence, EngineerReport
from agentic.workspace import CandidateWorkspace, create_workspace


DIGEST = "a" * 64
KEYS = [
    "virtual_column", "invalid_expressions", "source_cleaning",
    "revenue_formula", "regional_aggregation", "tests_and_readme",
]


def source(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "contracts").mkdir(parents=True)
    (root / "sales.csv").write_text("order,quantity\n1,2\n", encoding="utf-8")
    (root / "test_virtual_column.py").write_text("def test_original(): assert True\n", encoding="utf-8")
    (root / "contracts/data_policy.json").write_text('{"version":1}\n', encoding="utf-8")
    (root / "solution.py").write_text("def existing(): return 1\n", encoding="utf-8")
    return root


def ready_workspace(tmp_path: Path, mode: str = "rebuild") -> CandidateWorkspace:
    workspace = create_workspace(source(tmp_path), tmp_path / "candidate", mode)
    workspace.write_file("solution.py", "def add_virtual_column(df, role, name):\n    return df\n")
    if mode == "rebuild":
        workspace.write_file("pipeline.py", "def main():\n    return 1\n")
        workspace.write_file("README.md", "Readme explaining exact business rules.")
        workspace.write_file("tests/test_new.py", "def test_new():\n    assert True\n")
    workspace.request_validation("Request isolated secret-free candidate execution")
    return workspace


def actual_report(workspace: CandidateWorkspace) -> EngineerReport:
    files = workspace.validation_requests[-1]["files"]
    return EngineerReport(
        role="data_engineer",
        mode=workspace.mode,
        architect_report_sha256=DIGEST,
        summary="Actual executable candidate source written through trusted tools.",
        actual_files_written=[
            CandidateFileEvidence(
                path=f["path"], sha256=f["sha256"], requirement_keys=KEYS,
            ) for f in files
        ],
        validation_requested=True,
    )


def complete_ledger() -> EngineerLedger:
    ledger = EngineerLedger()
    for call in sorted(REQUIRED_CALLS):
        ledger.record(call)
    for name in ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json"):
        ledger.record("read_workspace_file", name)
    return ledger


def test_rebuild_requires_real_sha_matched_files():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        ws = ready_workspace(Path(folder))
        gate = evaluate_engineer(actual_report(ws), ws, complete_ledger(), DIGEST)
        assert gate.status == "CANDIDATE_READY_FOR_SANDBOX"
        assert len(gate.actual_written_files) == 4
        assert gate.validation_status == "PENDING_SANDBOX_VALIDATION"
        assert gate.failures == []


def test_improve_only_claims_modified_source(tmp_path: Path):
    ws = ready_workspace(tmp_path, "improve")
    gate = evaluate_engineer(actual_report(ws), ws, complete_ledger(), DIGEST)
    assert gate.status == "CANDIDATE_READY_FOR_SANDBOX"
    assert [x["path"] for x in gate.actual_written_files] == ["solution.py"]


def test_model_cannot_claim_a_file_it_never_wrote(tmp_path: Path):
    ws = ready_workspace(tmp_path)
    report = actual_report(ws)
    report.actual_files_written[0].sha256 = "0" * 64
    gate = evaluate_engineer(report, ws, complete_ledger(), DIGEST)
    assert gate.status == "INCOMPLETE"
    assert any("digest" in item for item in gate.failures)


@pytest.mark.parametrize("missing", sorted(REQUIRED_CALLS))
def test_missing_real_tool_is_incomplete(tmp_path: Path, missing: str):
    ws = ready_workspace(tmp_path)
    ledger = complete_ledger()
    ledger.calls.remove(missing)
    receipt = evaluate_engineer(actual_report(ws), ws, ledger, DIGEST)
    assert receipt.status == "INCOMPLETE"
    assert any("missing" in x.lower() for x in receipt.failures)


def test_missing_read_of_employer_original_tests_is_incomplete(tmp_path: Path):
    ws = ready_workspace(tmp_path)
    ledger = complete_ledger()
    ledger.read_paths.remove("test_virtual_column.py")
    gate = evaluate_engineer(actual_report(ws), ws, ledger, DIGEST)
    assert gate.status == "INCOMPLETE"
    assert any("not read" in x for x in gate.failures)


def test_missing_validation_request_is_not_a_pass(tmp_path: Path):
    ws = ready_workspace(tmp_path)
    report = actual_report(ws)
    ws.validation_requests.clear()
    gate = evaluate_engineer(report, ws, complete_ledger(), DIGEST)
    assert gate.status == "INCOMPLETE"


def test_fabricated_report_without_generated_files_fails(tmp_path: Path):
    ws = create_workspace(source(tmp_path), tmp_path / "candidate", "rebuild")
    report = EngineerReport(
        role="data_engineer", mode="rebuild", architect_report_sha256=DIGEST,
        summary="Model says all code is complete but actually wrote nothing.",
        actual_files_written=[
            CandidateFileEvidence(path="solution.py", sha256="0" * 64, requirement_keys=KEYS),
        ],
        validation_requested=True,
    )
    gate = evaluate_engineer(report, ws, complete_ledger(), DIGEST)
    assert gate.status == "INCOMPLETE"
    assert any("No real" in problem or "Rebuild" in problem for problem in gate.failures)


def test_wrong_architect_digest_cannot_pass(tmp_path: Path):
    ws = ready_workspace(tmp_path)
    report = actual_report(ws)
    report.architect_report_sha256 = "0" * 64
    gate = evaluate_engineer(report, ws, complete_ledger(), DIGEST)
    assert gate.status == "INCOMPLETE"
    assert any("different Architect" in x for x in gate.failures)
