"""Full-run telemetry contains only measured job and tool facts."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic.delivery_metrics import DeliveryTelemetryError, create_delivery_metrics


RUN_ID = "44485096373"
SHA = "a" * 40


def jobs():
    return {"jobs": [{
        "id": 12,
        "name": "architect",
        "status": "completed",
        "conclusion": "success",
        "started_at": "2026-11-19T08:10:00Z",
        "completed_at": "2026-11-19T08:10:35Z",
    }]}


def report(tmp_path: Path):
    return create_delivery_metrics(
        jobs_payload=jobs(), artifacts=tmp_path,
        run_id=RUN_ID, base_sha=SHA,
    )


def test_measured_jobs_are_not_confused_with_model_only_duration(tmp_path: Path):
    result = report(tmp_path)
    assert result["source"] == "real_github_jobs_and_independent_source_receipts"
    assert result["jobs"][0]["duration_ms"] == 35000.0
    assert result["jobs"][0]["measurement"] == "github_actions_job_started_and_completed_at"
    assert result["agent_measurements"]["data_architect"] is None
    assert result["model_token_usage"] is None
    assert result["model_cost"] is None
    assert result["otel_trace_id"] is None


def test_actual_instrumented_role_is_shown_without_unsafe_details(tmp_path: Path):
    path = tmp_path / "p2-architect-receipt"
    path.mkdir()
    (path / "role_telemetry.json").write_text(json.dumps({
        "schema_version": 1,
        "source": "measured_role_monotonic_clock",
        "role": "data_architect",
        "github_run_id": RUN_ID, "github_base_sha": SHA,
        "status": "success", "duration_ms": 123.6,
        "tool_call_count": 7,
        "model_deployment": "gpt-5.6-sol",
        "input_tokens": None, "output_tokens": None,
        "estimated_cost": None,
    }))
    result = report(tmp_path)
    assert result["agent_measurements"]["data_architect"]["duration_ms"] == 123.6
    assert result["agent_measurements"]["data_architect"]["tool_call_count"] == 7
    assert result["jobs"][0]["duration_ms"] == 35000


def test_forged_source_run_role_receipt_is_never_accepted(tmp_path: Path):
    path = tmp_path / "p2-architect-receipt"
    path.mkdir()
    (path / "role_telemetry.json").write_text(json.dumps({
        "schema_version": 1, "source": "measured_role_monotonic_clock",
        "role": "data_architect", "github_run_id": "999999",
        "github_base_sha": SHA,
        "status": "success", "duration_ms": 15,
        "tool_call_count": 7,
    }))
    with pytest.raises(DeliveryTelemetryError, match="stale"):
        report(tmp_path)


def test_p5_state_from_another_run_does_not_count_as_our_success(tmp_path: Path):
    path = tmp_path / "p5-bounded-run-state"
    path.mkdir()
    (path / "run_state.json").write_text(json.dumps({
        "github_run_id": "9999999", "base_commit_sha": SHA,
        "status": "WAITING_VERIFIER",
    }))
    with pytest.raises(DeliveryTelemetryError, match="P5 run-state"):
        report(tmp_path)


def test_github_job_metadata_missing_ids_is_not_fabricated(tmp_path: Path):
    with pytest.raises(DeliveryTelemetryError, match="Job IDs"):
        create_delivery_metrics(
            jobs_payload={"jobs": [{"name": "architect"}]},
            artifacts=tmp_path, run_id=RUN_ID, base_sha=SHA,
        )
