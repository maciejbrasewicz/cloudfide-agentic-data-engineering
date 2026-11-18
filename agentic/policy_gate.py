"""Fail-closed architecture gate: model text is not an approval or ground truth."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from contracts import DataPolicy

from .schemas.architect import ArchitectGateResult, ArchitectReport, SourceFacts


REQUIRED_TOOLS = frozenset({
    "read_spec", "inspect_original_tests", "profile_source",
    "inspect_orders", "reconcile_raw_control", "inspect_approved_policy",
    "validate_policy_proposal",
})
REQUIRED_REQUIREMENTS = frozenset({
    "virtual_column", "invalid_expressions", "source_cleaning",
    "revenue_formula", "regional_aggregation", "tests_and_readme",
})
REQUIRED_DECISIONS = frozenset({
    "source_control", "duplicates", "negative_quantity",
    "missing_unit_price", "missing_discount", "region",
})
DECISION_EVIDENCE = {
    "source_control": {"source_controls"},
    "duplicates": {"source_profile", "source_controls"},
    "negative_quantity": {"source_profile"},
    "missing_unit_price": {"source_profile"},
    "missing_discount": {"task_spec"},
    "region": {"source_profile"},
}
DECISION_CLASSIFICATION = {
    "source_control": "data_integrity",
    "duplicates": "business_assumption",
    "negative_quantity": "business_assumption",
    "missing_unit_price": "business_assumption",
    "missing_discount": "specified",
    "region": "repair_policy",
}


def policy_sha(policy: DataPolicy) -> str:
    normalized = json.dumps(
        policy.model_dump(mode="json"), ensure_ascii=False,
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class ArchitectToolLedger:
    """Private tool-execution receipts generated only inside trusted Python functions."""

    calls: list[str] = field(default_factory=list)
    validated_policy_hashes: set[str] = field(default_factory=set)

    def record(self, name: str) -> None:
        if name not in REQUIRED_TOOLS:
            raise ValueError("Unknown Architect tool")
        self.calls.append(name)

    def record_validated_policy(self, policy: DataPolicy) -> None:
        self.validated_policy_hashes.add(policy_sha(policy))
        self.record("validate_policy_proposal")


def _unique_exact(items: list[str], expected: frozenset[str]) -> bool:
    return len(items) == len(expected) and set(items) == expected


def evaluate_architect(
    report: ArchitectReport, *, trusted_facts: SourceFacts,
    task_spec_sha256: str, approved_policy: DataPolicy, tool_ledger: ArchitectToolLedger,
) -> ArchitectGateResult:
    """Compare the agent's exact claims with independently observed source data."""
    problems: list[str] = []
    seen = set(tool_ledger.calls)
    missing_tools = REQUIRED_TOOLS - seen
    if missing_tools:
        problems.append("Required real tool calls missing: " + ", ".join(sorted(missing_tools)))
    if report.task_spec_sha256 != task_spec_sha256:
        problems.append("Task specification digest mismatch")
    if report.observed_facts != trusted_facts:
        problems.append("Architect facts disagree with the independent original CSV profiler")
    if not report.observed_facts.control_reconciled:
        problems.append("Architect did not prove the raw TOTAL reconciliation")

    requirements = [item.key for item in report.requirements]
    if not _unique_exact(requirements, REQUIRED_REQUIREMENTS):
        problems.append("Missing, duplicated or unsupported recruitment requirements")
    for item in report.requirements:
        if "task_spec" not in item.evidence_refs:
            problems.append("Requirement not tied to the original task: " + item.key)
        if item.key in {"virtual_column", "invalid_expressions"} and "original_tests" not in item.evidence_refs:
            problems.append("Virtual-column requirement not tied to original tests: " + item.key)

    decisions = [item.field for item in report.decisions]
    if not _unique_exact(decisions, REQUIRED_DECISIONS):
        problems.append("Missing, duplicated or unsupported policy decisions")
    for item in report.decisions:
        if item.proposed_value != getattr(report.proposed_policy, item.field):
            problems.append("Policy decision differs from proposed contract: " + item.field)
        if item.classification != DECISION_CLASSIFICATION[item.field]:
            problems.append("Incorrect decision classification: " + item.field)
        if not DECISION_EVIDENCE[item.field].issubset(item.evidence_refs):
            problems.append("Missing source evidence on policy decision: " + item.field)
    if policy_sha(report.proposed_policy) not in tool_ledger.validated_policy_hashes:
        problems.append("Final proposed policy was not checked through the real policy tool")

    proposed = report.proposed_policy.model_dump(mode="json")
    approved = approved_policy.model_dump(mode="json")
    difference = {
        name: {"approved": str(approved[name]), "proposed": str(value)}
        for name, value in proposed.items() if approved[name] != value
    }
    digest = hashlib.sha256(
        report.model_dump_json(exclude_none=True).encode("utf-8")
    ).hexdigest()
    status = (
        "INCOMPLETE" if problems else
        "AWAITING_HUMAN_APPROVAL" if difference else
        "APPROVED_FOR_ENGINEERING"
    )
    return ArchitectGateResult(
        status=status,
        report_sha256=digest,
        task_spec_sha256=task_spec_sha256,
        source_sha256=trusted_facts.source_sha256,
        verified_tool_calls=list(tool_ledger.calls),
        policy_diff=difference,
        failures=problems,
    )
