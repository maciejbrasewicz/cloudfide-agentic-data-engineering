"""Only independently verified Architect policy changes may reach human review."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agentic.policy_gate import REQUIRED_TOOLS
from agentic.policy_review_request import PolicyReviewError, prepare_human_review
from pipeline import ROOT


RUN = "44485096373"
SOURCE = "a" * 64
SPEC = "b" * 64


def make_case(tmp_path: Path):
    repo = tmp_path / "repo"
    evidence = tmp_path / "evidence"
    (repo / "contracts").mkdir(parents=True)
    evidence.mkdir()
    source = (ROOT / "contracts/data_policy.json").read_bytes()
    policy_file = repo / "contracts/data_policy.json"
    policy_file.write_bytes(source)
    baseline = json.loads(source)
    proposed = {**baseline, "duplicates": "keep_all"}
    diff = {"duplicates": {
        "approved": "remove_exact_duplicates", "proposed": "keep_all",
    }}
    (evidence / "architect_gate.json").write_text(json.dumps({
        "status": "AWAITING_HUMAN_APPROVAL",
        "verified_tool_calls": sorted(REQUIRED_TOOLS),
        "source_sha256": SOURCE, "task_spec_sha256": SPEC,
        "policy_diff": diff, "failures": [],
    }))
    (evidence / "input_manifest.json").write_text(json.dumps({
        "run_id": RUN, "source_csv_sha256": SOURCE, "specification_sha256": SPEC,
        "approved_policy_sha256": hashlib.sha256(source).hexdigest(),
    }))
    (evidence / "contract_proposal.json").write_text(json.dumps({
        "source_sha256": SOURCE, "specification_sha256": SPEC,
        "proposed_policy": proposed,
    }))
    return repo, evidence


def test_real_policy_change_produces_review_request_without_applying_it(tmp_path: Path):
    repo, evidence = make_case(tmp_path)
    old = (repo / "contracts/data_policy.json").read_bytes()
    issue = prepare_human_review(evidence, repo, RUN)
    assert "**NOT APPROVED.**" in issue
    assert "keep_all" in issue
    assert "remove_exact_duplicates" in issue
    assert "/actions/runs/" + RUN in issue
    assert "contracts/data_policy.json" in issue
    assert (repo / "contracts/data_policy.json").read_bytes() == old
    assert "original private task text" in issue.lower()


@pytest.mark.parametrize("status", ["APPROVED_FOR_ENGINEERING", "INCOMPLETE"])
def test_no_unapproved_issue_for_other_states(tmp_path: Path, status: str):
    repo, evidence = make_case(tmp_path)
    path = evidence / "architect_gate.json"
    gate = json.loads(path.read_text())
    gate["status"] = status
    path.write_text(json.dumps(gate))
    assert prepare_human_review(evidence, repo, RUN) is None


@pytest.mark.parametrize("attack", ["source_sha", "report_diff", "missing_tool", "policy_hash", "changed_run"])
def test_forged_architect_policy_diff_is_rejected(tmp_path: Path, attack: str):
    repo, evidence = make_case(tmp_path)
    gate_path = evidence / "architect_gate.json"
    manifest_path = evidence / "input_manifest.json"
    gate = json.loads(gate_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    if attack == "source_sha":
        gate["source_sha256"] = "0" * 64
    elif attack == "report_diff":
        gate["policy_diff"]["duplicates"]["proposed"] = "reject"
    elif attack == "missing_tool":
        gate["verified_tool_calls"].remove("read_spec")
    elif attack == "policy_hash":
        manifest["approved_policy_sha256"] = "0" * 64
    else:
        manifest["run_id"] = "12345678"
    gate_path.write_text(json.dumps(gate))
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(PolicyReviewError):
        prepare_human_review(evidence, repo, RUN)


def test_illegal_model_policy_value_does_not_get_approved(tmp_path: Path):
    repo, evidence = make_case(tmp_path)
    file = evidence / "contract_proposal.json"
    obj = json.loads(file.read_text())
    obj["proposed_policy"]["duplicates"] = "execute_python"
    file.write_text(json.dumps(obj))
    with pytest.raises(ValueError):
        prepare_human_review(evidence, repo, RUN)
