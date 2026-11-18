"""Instantiate seven real Engineer tools against the pinned Agent Framework SDK."""
from __future__ import annotations

import hashlib

import pytest


def test_engineer_sdk_exposes_scoped_tools_without_running_candidate(tmp_path):
    pytest.importorskip("agent_framework")
    from agent_framework import Agent
    from agent_framework.foundry import FoundryChatClient

    from agentic.engineer import engineer_tools
    from agentic.engineer_gate import EngineerLedger, REQUIRED_CALLS
    from agentic.spec_loader import TaskSpec
    from agentic.workspace import CandidateWorkspace

    raw = "Original task source is never written to a tracked file"
    spec = TaskSpec(
        text=raw, sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        source="actions_secret",
    )
    ledger = EngineerLedger()
    workspace = CandidateWorkspace(
        root=tmp_path, mode="rebuild", protected_hashes={},
    )
    tools = engineer_tools(spec, None, workspace, ledger)
    assert {item.name for item in tools} == REQUIRED_CALLS
    assert len(tools) == 7
    assert ledger.calls == []
    assert workspace.writes == []
    assert Agent and FoundryChatClient
