"""Independent P2 admission gate. LLM claims are never evidence of file writes."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .patch_policy import is_candidate_path
from .schemas.engineer import EngineerReport
from .workspace import CandidateWorkspace, _safe, _sha


REQUIRED_CALLS = frozenset({
    "read_spec", "read_architect_contract", "list_workspace",
    "read_workspace_file", "write_candidate_file", "show_diff", "request_validation",
})
REQUIRED_READS = frozenset({
    "sales.csv", "test_virtual_column.py", "contracts/data_policy.json",
})
REBUILD_CORE = frozenset({"solution.py", "pipeline.py", "README.md"})
REQUIRED_KEYS = frozenset({
    "virtual_column", "invalid_expressions", "source_cleaning",
    "revenue_formula", "regional_aggregation", "tests_and_readme",
})


@dataclass
class EngineerLedger:
    """Trusted function calls and paths. No model-provided text stored here."""

    calls: list[str] = field(default_factory=list)
    read_paths: set[str] = field(default_factory=set)

    def record(self, name: str, path: str | None = None) -> None:
        if name not in REQUIRED_CALLS:
            raise ValueError("Unknown Engineer tool")
        self.calls.append(name)
        if name == "read_workspace_file" and path is not None:
            self.read_paths.add(path)


class EngineerGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["CANDIDATE_READY_FOR_SANDBOX", "INCOMPLETE"]
    report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    architect_report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    verified_tool_calls: list[str]
    actual_written_files: list[dict[str, str]]
    failures: list[str] = Field(default_factory=list)
    validation_status: Literal["PENDING_SANDBOX_VALIDATION"]


def evaluate_engineer(
    report: EngineerReport, workspace: CandidateWorkspace,
    ledger: EngineerLedger, expected_architect_digest: str,
) -> EngineerGateResult:
    problems: list[str] = []
    workspace.verify_protected()
    all_files = workspace.list_files()
    actual_files = [name for name in all_files if is_candidate_path(name)]
    if report.architect_report_sha256 != expected_architect_digest:
        problems.append("Report references a different Architect run")
    if report.mode != workspace.mode:
        problems.append("Report mode differs from actual candidate workspace")
    missed = REQUIRED_CALLS - set(ledger.calls)
    if missed:
        problems.append("Real Engineer tool calls missing: " + ", ".join(sorted(missed)))
    unread = REQUIRED_READS - ledger.read_paths
    if unread:
        problems.append("Original employer inputs not read: " + ", ".join(sorted(unread)))
    if not workspace.validation_requests or not report.validation_requested:
        problems.append("Independent validation was not requested")
    if workspace.mode == "rebuild" and not REBUILD_CORE.issubset(actual_files):
        problems.append("Rebuild did not create the three core deliverables")
    if workspace.mode == "rebuild" and not any(name.startswith("tests/test_") for name in actual_files):
        problems.append("Rebuild did not create its own executable tests")
    for name in actual_files:
        if workspace.mode == "rebuild" and name not in {x["path"] for x in workspace.writes}:
            problems.append("Rebuild candidate did not come from real write tools: " + name)

    published = report.actual_files_written
    if len({item.path for item in published}) != len(published):
        problems.append("Duplicate file claims in model report")
    if {item.path for item in published} != set(actual_files):
        problems.append("Model file claims differ from actual candidate file tree")
    observed_sha = {
        name: _sha(_safe(workspace.root, name).read_bytes())
        for name in actual_files
    }
    for item in published:
        if observed_sha.get(item.path) != item.sha256:
            problems.append("Claimed file digest disagrees with on-disk bytes: " + item.path)
    mapped = {key for item in published for key in item.requirement_keys}
    if not REQUIRED_KEYS.issubset(mapped):
        problems.append("Missing required task-to-code evidence mapping")
    if any(
        request.get("status") != "PENDING_SANDBOX_VALIDATION"
        or {item["path"] for item in request["files"]} != set(actual_files)
        for request in workspace.validation_requests
    ):
        problems.append("Validation request hashes or scope differ from written candidate")
    if not workspace.writes:
        problems.append("No real model-supplied file writes")
    digest = hashlib.sha256(report.model_dump_json().encode("utf-8")).hexdigest()
    return EngineerGateResult(
        status="INCOMPLETE" if problems else "CANDIDATE_READY_FOR_SANDBOX",
        report_sha256=digest,
        architect_report_sha256=expected_architect_digest,
        verified_tool_calls=list(ledger.calls),
        actual_written_files=[
            {"path": name, "sha256": observed_sha[name]} for name in actual_files
        ],
        failures=problems,
        validation_status="PENDING_SANDBOX_VALIDATION",
    )
