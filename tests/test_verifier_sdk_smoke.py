"""Live SDK schema and source review of the Verifier tool and job boundary."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


def test_verifier_uses_real_pinned_foundry_tool_interfaces(tmp_path: Path):
    pytest.importorskip("agent_framework")
    from agentic.spec_loader import TaskSpec
    from agentic.verifier import verifier_tools
    from agentic.verifier_gate import REQUIRED_TOOLS, VerifierLedger

    text = "Synthetic confidential instruction fixture - never committed"
    spec = TaskSpec(
        text=text, sha256=hashlib.sha256(text.encode()).hexdigest(),
        source="actions_secret",
    )
    ledger = VerifierLedger()
    tools = verifier_tools(
        spec=spec, candidate_dir=tmp_path,
        p3_receipt={"status": "PASSED", "reconciliation": "passed"},
        candidate_digest="a" * 64, p3_digest="b" * 64,
        ledger=ledger,
    )
    assert len(tools) == 7
    assert {item.name for item in tools} == REQUIRED_TOOLS
    assert ledger.calls == []  # Declaring tools isn't executing them.


def test_verifier_workflow_preserves_azure_vs_untrusted_execution_boundary():
    yaml = pytest.importorskip("yaml")
    root = Path(__file__).resolve().parents[1]
    jobs = yaml.safe_load(
        (root / ".github/workflows/engineer-e2e.yml").read_text(encoding="utf-8")
    )["jobs"]
    assert {"verifier", "adversarial", "p5-state"}.issubset(jobs)
    assert jobs["verifier"]["needs"] == ["p5-state"]
    assert jobs["verifier"]["permissions"]["id-token"] == "write"
    assert jobs["adversarial"]["needs"] == "verifier"
    assert jobs["adversarial"]["permissions"] == {"contents": "read"}
    assert all("azure/login" not in str(step) for step in jobs["adversarial"]["steps"])
    assert all("CLOUDFIDE_TASK_SPEC" not in str(step) for step in jobs["adversarial"]["steps"])
