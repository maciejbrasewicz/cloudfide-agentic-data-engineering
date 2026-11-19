"""Pinned Foundry SDK and Actions YAML smoke for actual multi-round rework."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


def test_rework_tools_are_real_agent_framework_tools(tmp_path: Path):
    pytest.importorskip("agent_framework")

    from agentic.engineer_gate import EngineerLedger
    from agentic.rework import ReworkLedger, rework_tools
    from agentic.spec_loader import TaskSpec
    from agentic.workspace import CandidateWorkspace

    text = "Synthetic task input, not the employer's private specification"
    spec = TaskSpec(
        text=text, sha256=hashlib.sha256(text.encode()).hexdigest(),
        source="actions_secret",
    )
    workspace = CandidateWorkspace(
        root=tmp_path / "candidate", mode="rebuild", protected_hashes={},
    )
    tools = rework_tools(
        spec=spec, architect=None, workspace=workspace,
        engineer_ledger=EngineerLedger(), rework_ledger=ReworkLedger(),
        prior_root=tmp_path / "prior", verdict={"status": "FAILED"},
        feedback_dir=tmp_path / "logs", architect_digest="b" * 64,
    )
    assert len(tools) == 9
    assert {tool.name for tool in tools} == {
        "read_spec", "read_architect_contract", "list_workspace",
        "read_workspace_file", "write_candidate_file", "show_diff",
        "request_validation", "read_failure_evidence",
        "read_previous_candidate",
    }


def test_p5_workflow_has_strict_bounded_dag():
    yaml = pytest.importorskip("yaml")
    root = Path(__file__).resolve().parents[1]
    data = yaml.safe_load((root / ".github/workflows/engineer-e2e.yml").read_text())
    jobs = data["jobs"]
    assert {
        "architect", "engineer", "sandbox-validate",
        "rework-r2", "sandbox-rework-r2",
        "rework-r3", "sandbox-rework-r3", "p5-state",
    }.issubset(jobs)
    assert jobs["rework-r2"]["needs"] == ["architect", "engineer", "sandbox-validate"]
    assert jobs["rework-r3"]["needs"] == ["architect", "rework-r2", "sandbox-rework-r2"]
    assert jobs["p5-state"]["needs"] == [
        "architect", "engineer", "sandbox-validate",
        "rework-r2", "sandbox-rework-r2",
        "rework-r3", "sandbox-rework-r3",
    ]
    for key in ("sandbox-validate", "sandbox-rework-r2", "sandbox-rework-r3"):
        assert jobs[key]["permissions"] == {"contents": "read"}
        assert all("azure/login" not in str(step) for step in jobs[key]["steps"])
        assert "candidate_status" in jobs[key]["outputs"]
    assert jobs["p5-state"]["permissions"] == {"contents": "read"}
