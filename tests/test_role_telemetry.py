"""Role telemetry only reports measured time; no generated content or guessed spend."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic.role_telemetry import measure_role


def test_measured_foundry_invocation_is_privacy_safe(tmp_path: Path):
    private_task = "DO_NOT_EXPOSE_PRIVATE_ORIGINAL_ASSIGNMENT"
    with measure_role(
        role="data_engineer", output_dir=tmp_path,
        model_deployment="gpt-5.6-sol", tool_call_count=lambda: 9,
    ):
        assert private_task
    result = json.loads((tmp_path / "role_telemetry.json").read_text())
    assert result["source"] == "measured_role_monotonic_clock"
    assert result["status"] == "success"
    assert result["role"] == "data_engineer"
    assert result["duration_ms"] >= 0
    assert result["tool_call_count"] == 9
    assert result["input_tokens"] is None
    assert result["output_tokens"] is None
    assert result["estimated_cost"] is None
    assert private_task not in json.dumps(result)


def test_raised_model_error_creates_real_failure_receipt(tmp_path: Path):
    with pytest.raises(RuntimeError, match="model execution failed"):
        with measure_role(
            role="verification_engineer", output_dir=tmp_path,
            model_deployment="gpt-5.6-sol", tool_call_count=lambda: 2,
        ):
            raise RuntimeError("model execution failed")
    result = json.loads((tmp_path / "role_telemetry.json").read_text())
    assert result["status"] == "error"
    assert result["tool_call_count"] == 2


def test_unknown_role_is_not_allowed_to_masquerade_as_real_agent(tmp_path: Path):
    with pytest.raises(ValueError, match="Unknown"):
        with measure_role(
            role="oracle_report_fabricator", output_dir=tmp_path,
            model_deployment="gpt-5.6-sol", tool_call_count=lambda: 0,
        ):
            pass
    assert not (tmp_path / "role_telemetry.json").exists()
