"""P1 integration smoke: instantiate all seven real Microsoft Agent Framework tools.

Quality-only CI may skip this; the Foundry SDK workflow installs the locked
Foundry dependency group and must execute this test against the pinned SDK.
"""
from __future__ import annotations

import hashlib

import pytest


def test_architect_tool_schema_instantiation_against_pinned_agent_framework():
    pytest.importorskip("agent_framework")
    from agent_framework import Agent
    from agent_framework.foundry import FoundryChatClient

    from agentic.architect import build_architect_tools
    from agentic.policy_gate import ArchitectToolLedger, REQUIRED_TOOLS
    from agentic.spec_loader import TaskSpec
    from pipeline import ROOT

    spec_text = "A synthetic no-secret virtual column assignment for SDK smoke"
    spec = TaskSpec(
        text=spec_text,
        sha256=hashlib.sha256(spec_text.encode("utf-8")).hexdigest(),
        source="actions_secret",
    )
    ledger = ArchitectToolLedger()
    tools = build_architect_tools(spec=spec, root=ROOT, ledger=ledger)
    assert len(tools) == 7
    assert {tool.name for tool in tools} == REQUIRED_TOOLS
    assert not ledger.calls  # Definition of SDK tools is NOT executing a tool.
    assert Agent and FoundryChatClient
