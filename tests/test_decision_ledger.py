"""Human approval is a security boundary, not an attribute an LLM may set."""
import json

import pytest
from pydantic import ValidationError

from agentic.decision_ledger import DataDecision, DecisionLedger, create_ledger, write_ledger_atomic


def _manifest():
    return {
        "git_revision": "f" * 40,
        "provenance": {"source_sha256": "a" * 64},
        "agent_reviews": [
            {
                "role": role,
                "summary": "Observed real source behavior under review",
                "findings": [],
                "recommended_next_action": "Ask the owner to approve the business policy",
                "decision_proposals": [
                    {
                        "target": "duplicates",
                        "proposal": "Remove source-exact duplicate lines after validating control row",
                        "evidence": "Five duplicate records are present in the raw export",
                        "risk": "Identical order lines might correspond to separate orders",
                    },
                ] if i == 0 else [],
            }
            for i, role in enumerate(("data_architect", "data_engineer", "verification_engineer"))
        ],
    }


def test_ledger_persists_only_actual_proposals_without_autoapproval(tmp_path):
    ledger = create_ledger(_manifest())
    assert len(ledger.decisions) == 1
    decision = ledger.decisions[0]
    assert decision.id == "DD-0001"
    assert decision.role == "data_architect"
    assert decision.status == "pending_human_review"
    assert decision.approved_by is None
    assert len(decision.source_report_sha256) == 64
    dest = tmp_path / "decisions" / "pending.json"
    write_ledger_atomic(ledger, dest)
    stored = DecisionLedger.model_validate_json(dest.read_text(encoding="utf-8"))
    assert stored == ledger
    assert not list(dest.parent.glob(".data-decisions-*"))


@pytest.mark.parametrize("patch", [
    {"status": "approved"},
    {"approved_by": "LLM"},
    {"role": "operator"},
    {"proposal": "tiny"},
    {"source_report_sha256": "not-a-hash"},
    {"unknown_parameter": "injected"},
])
def test_agent_cannot_approve_or_escape_proposal_contract(patch):
    base = create_ledger(_manifest()).decisions[0].model_dump()
    base.update(patch)
    with pytest.raises(ValidationError):
        DataDecision.model_validate(base)


def test_preexisting_old_reports_still_parse_and_produce_empty_ledger():
    manifest = _manifest()
    for report in manifest["agent_reviews"]:
        report.pop("decision_proposals")
    assert create_ledger(manifest).decisions == []


def test_ledger_wont_accept_duplicated_ids():
    first = create_ledger(_manifest()).decisions[0]
    with pytest.raises(ValidationError, match="Duplicate"):
        DecisionLedger(
            generated_at_utc="2026-11-18T00:00:00Z",
            source_manifest_sha256="0" * 64,
            decisions=[first, first],
        )
