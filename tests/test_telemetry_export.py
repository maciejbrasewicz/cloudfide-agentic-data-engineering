"""Public telemetry exporter must not leak model content or invent metrics."""
import copy
import json

import pytest

from agentic.telemetry_export import make_public_trace


@pytest.fixture
def run():
    return {
        "generated_at_utc": "2026-11-18T12:00:00Z",
        "git_revision": "c" * 40,
        "model_deployment": "gpt-5.6-sol",
        "provenance": {"source_sha256": "a" * 64},
        "deterministic_attestation": {
            "provenance_matched": True,
            "three_structured_agent_reports": True,
            "deterministic_reconciliation_confirmed": True,
        },
        "agent_reviews": [{
            "role": "data_architect",
            "summary": "PRIVATE_MODEL_TEXT_DO_NOT_PUBLISH",
        }],
        "observability": {
            "schema_version": 1,
            "source": "measured_runtime",
            "wall_duration_ms": 110.5,
            "tool_call_count": 1,
            "tool_events": [{
                "kind": "tool_call",
                "name": "profile_source",
                "started_at_utc": "2026-11-18T12:00:01Z",
                "duration_ms": 9.25,
                "status": "ok",
                "measurement": "runtime_clock",
            }],
            "github_run_id": "123456",
            "trace_id": None,
            "otel_exporter_configured": False,
        },
    }


def test_public_trace_exports_measured_numbers_without_model_text(run):
    value = make_public_trace(run)
    assert value["tool_call_count"] == 1
    assert value["tool_counts"] == {"profile_source": 1}
    assert value["wall_duration_ms"] == 110.5
    assert value["estimated_model_cost"] is None
    assert value["model_token_usage"] is None
    assert "PRIVATE_MODEL_TEXT_DO_NOT_PUBLISH" not in json.dumps(value)


@pytest.mark.parametrize("tamper", [
    lambda v: v["observability"].update(tool_call_count=2),
    lambda v: v["observability"]["tool_events"][0].update(args={"private": "secret"}),
    lambda v: v["observability"]["tool_events"][0].update(name="arbitrary_shell"),
    lambda v: v["observability"].update(wall_duration_ms=-1),
    lambda v: v["deterministic_attestation"].update(provenance_matched=False),
])
def test_public_trace_rejects_untrusted_or_incomplete_manifest(run, tamper):
    tampered = copy.deepcopy(run)
    tamper(tampered)
    with pytest.raises(ValueError):
        make_public_trace(tampered)
