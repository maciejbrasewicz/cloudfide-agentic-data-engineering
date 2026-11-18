"""P1 requires genuine source evidence and each mandatory tool invocation."""
from __future__ import annotations

from pathlib import Path

import pytest

from contracts import DataPolicy, read_policy
from pipeline import ROOT
from agentic.policy_gate import ArchitectToolLedger, REQUIRED_TOOLS, evaluate_architect
from agentic.schemas.architect import ArchitectReport, PolicyDecision, Requirement
from agentic.source_tools import (
    SourceEvidenceError, inspect_original_order_ids, original_tests, source_facts,
)

EXPECTED_REQUIREMENTS = (
    "virtual_column", "invalid_expressions", "source_cleaning",
    "revenue_formula", "regional_aggregation", "tests_and_readme",
)
DECISION_CASES = (
    ("source_control", "data_integrity", ["source_controls"]),
    ("duplicates", "business_assumption", ["source_profile", "source_controls"]),
    ("negative_quantity", "business_assumption", ["source_profile"]),
    ("missing_unit_price", "business_assumption", ["source_profile"]),
    ("missing_discount", "specified", ["task_spec"]),
    ("region", "repair_policy", ["source_profile"]),
)
SPEC_DIGEST = "1" * 64


def _policy() -> DataPolicy:
    return read_policy(ROOT / "contracts/data_policy.json")


def _ledger(policy: DataPolicy | None = None) -> ArchitectToolLedger:
    ledger = ArchitectToolLedger()
    for name in sorted(REQUIRED_TOOLS - {"validate_policy_proposal"}):
        ledger.record(name)
    ledger.record_validated_policy(policy or _policy())
    return ledger


def _report(policy: DataPolicy | None = None) -> ArchitectReport:
    contract = policy or _policy()
    requirements = [
        Requirement(
            key=key,
            implementation_expectation="Implement and prove this source requirement on original input.",
            evidence_refs=["task_spec", "original_tests"]
            if key in {"virtual_column", "invalid_expressions"} else ["task_spec"],
        )
        for key in EXPECTED_REQUIREMENTS
    ]
    decisions = [
        PolicyDecision(
            field=key,
            proposed_value=getattr(contract, key),
            classification=classification,
            justification="Justification is grounded in original source measurements and the assignment.",
            risk="Business interpretation might require source-owner confirmation.",
            evidence_refs=refs,
        )
        for key, classification, refs in DECISION_CASES
    ]
    return ArchitectReport(
        role="data_architect",
        task_spec_sha256=SPEC_DIGEST,
        summary="Complete source-grounded architecture for the original virtual-column task.",
        requirements=requirements,
        observed_facts=source_facts(ROOT),
        proposed_policy=contract,
        decisions=decisions,
        unresolved_business_questions=[
            "Are identical order lines actual duplicate exports?",
            "Do negative quantities represent accounting returns?",
            "Are inferred historical product prices contractually valid?",
        ],
        suggested_validation_cases=[
            "Reject unsupported arithmetic and unknown column names.",
            "Reconcile raw TOTAL before removing duplicates.",
            "Compute line revenue with exact Decimal and approved discount rules.",
            "Recompute region totals independently of production pipeline code.",
        ],
    )


def _gate(report: ArchitectReport, ledger: ArchitectToolLedger):
    return evaluate_architect(
        report, trusted_facts=source_facts(ROOT),
        task_spec_sha256=SPEC_DIGEST, approved_policy=_policy(),
        tool_ledger=ledger,
    )


def test_real_csv_independent_source_profile_is_precise():
    facts = source_facts(ROOT)
    assert facts.source_rows == 1507
    assert facts.transaction_rows == 1505
    assert facts.repeated_header_rows == 1
    assert facts.total_control_rows == 1
    assert facts.exact_duplicate_extra_rows == 5
    assert facts.missing_unit_price_rows == 4
    assert facts.negative_quantity_rows == 6
    assert facts.noncanonical_region_rows == 15
    assert facts.blank_discount_rows == 963  # Raw: before duplicate removal.
    assert facts.comma_price_rows >= 7
    assert facts.spaced_quantity_rows >= 4
    assert facts.raw_quantity_total == facts.control_quantity == 37150
    assert facts.raw_discount_total == facts.control_discount == "65924.67"
    assert facts.control_reconciled


def test_profiler_does_not_import_production_pipeline():
    import ast

    code = (ROOT / "agentic/source_tools.py").read_text(encoding="utf-8")
    parsed = ast.parse(code)
    names = [alias.name for node in ast.walk(parsed) if isinstance(node, ast.Import) for alias in node.names]
    modules = [node.module for node in ast.walk(parsed) if isinstance(node, ast.ImportFrom)]
    assert "pandas" not in names
    assert not {"pipeline", "solution", "dataframe_contracts"} & set(modules)


def test_source_controls_fail_closed_on_mutated_total(tmp_path: Path):
    original = (ROOT / "sales.csv").read_bytes()
    lines = original.decode("utf-8").splitlines()
    control = next(i for i, line in enumerate(lines) if line.startswith("TOTAL,"))
    lines[control] = lines[control].replace("37150", "37151", 1)
    (tmp_path / "sales.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(SourceEvidenceError, match="TOTAL disagrees"):
        source_facts(tmp_path)


def test_source_rejects_unknown_row_kind(tmp_path: Path):
    raw = (ROOT / "sales.csv").read_bytes()
    (tmp_path / "sales.csv").write_bytes(raw.replace(b"SO-10001", b"XX-10001", 1))
    with pytest.raises(SourceEvidenceError, match="Unknown source row kind"):
        source_facts(tmp_path)


def test_original_test_inspector_reads_supplied_fixture_only():
    result = original_tests(ROOT)
    assert "test_sum_of_two_columns" in result["content"]
    assert len(result["sha256"]) == 64
    assert "def add_virtual_column(" not in result["content"]


def test_order_inspector_requires_existing_order_ids():
    result = inspect_original_order_ids(ROOT, "SO-10001")
    assert "SO-10001" in result
    with pytest.raises(SourceEvidenceError, match="valid original"):
        inspect_original_order_ids(ROOT, "../../secrets")
    with pytest.raises(SourceEvidenceError, match="No original"):
        inspect_original_order_ids(ROOT, "SO-99999")


def test_evidenced_architecture_passes_only_verified_gate():
    receipt = _gate(_report(), _ledger())
    assert receipt.status == "APPROVED_FOR_ENGINEERING"
    assert receipt.failures == []
    assert receipt.policy_diff == {}
    assert set(receipt.verified_tool_calls) == REQUIRED_TOOLS


@pytest.mark.parametrize("missing", sorted(REQUIRED_TOOLS))
def test_any_missing_actual_tool_call_is_incomplete(missing: str):
    ledger = _ledger()
    ledger.calls.remove(missing)
    receipt = _gate(_report(), ledger)
    assert receipt.status == "INCOMPLETE"
    assert any("tool calls missing" in error for error in receipt.failures)


def test_invented_source_numbers_fail():
    report = _report()
    changed = report.observed_facts.model_copy(update={"exact_duplicate_extra_rows": 7})
    receipt = _gate(report.model_copy(update={"observed_facts": changed}), _ledger())
    assert receipt.status == "INCOMPLETE"
    assert any("disagree" in error for error in receipt.failures)


def test_policy_change_awaits_explicit_human_approval():
    proposal = _policy().model_copy(update={"duplicates": "keep_all"})
    receipt = _gate(_report(proposal), _ledger(proposal))
    assert receipt.status == "AWAITING_HUMAN_APPROVAL"
    assert receipt.policy_diff["duplicates"] == {
        "approved": "remove_exact_duplicates", "proposed": "keep_all",
    }


def test_model_cannot_validate_one_policy_and_output_another():
    proposal = _policy().model_copy(update={"duplicates": "keep_all"})
    receipt = _gate(_report(proposal), _ledger())
    assert receipt.status == "INCOMPLETE"
    assert any("not checked" in error for error in receipt.failures)


def test_missing_requirement_and_duplicated_decision_fail():
    report = _report()
    receipt = _gate(report.model_copy(update={
        "requirements": report.requirements[:-1],
        "decisions": report.decisions[:-1] + [report.decisions[0]],
    }), _ledger())
    assert receipt.status == "INCOMPLETE"
    assert any("requirements" in reason for reason in receipt.failures)
    assert any("decisions" in reason for reason in receipt.failures)


def test_decisions_without_source_provenance_fail():
    report = _report()
    updated = [
        d.model_copy(update={"evidence_refs": ["approved_policy"]})
        if d.field == "duplicates" else d for d in report.decisions
    ]
    receipt = _gate(report.model_copy(update={"decisions": updated}), _ledger())
    assert receipt.status == "INCOMPLETE"
    assert any("source evidence" in reason for reason in receipt.failures)


def test_wrong_task_spec_hash_cannot_be_accepted():
    receipt = _gate(
        _report().model_copy(update={"task_spec_sha256": "0" * 64}),
        _ledger(),
    )
    assert receipt.status == "INCOMPLETE"
    assert any("digest mismatch" in reason for reason in receipt.failures)
