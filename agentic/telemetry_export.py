"""Export a small, privacy-safe measured trace from an attested Foundry report.

Historical tool arguments and outputs MUST NOT be serialized into this public file.
Per-agent wall time and token counts are emitted only if genuinely captured.\nEstimated billing cost remains null without verified model pricing.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .verify import verify_manifest
from pipeline import ROOT

APPROVED_TOOLS = frozenset({
    "profile_source", "inspect_orders", "read_project_file",
    "check_quality", "inspect_approved_policy", "inspect_reconciliation",
})


def make_public_trace(manifest: dict) -> dict:
    obs = manifest["observability"]
    if obs.get("schema_version") != 1 or obs.get("source") != "measured_runtime":
        raise ValueError("Missing measured telemetry contract")
    events = obs.get("tool_events")
    if not isinstance(events, list):
        raise ValueError("Missing tool events")
    if len(events) != obs.get("tool_call_count") or not events:
        raise ValueError("Expected at least one recorded tool call")
    if any(
        event.get("name") not in APPROVED_TOOLS
        or event.get("measurement") != "runtime_clock"
        or event.get("status") not in ("ok", "error")
        or not isinstance(event.get("duration_ms"), (int, float))
        or event["duration_ms"] < 0
        or set(event) != {
            "kind", "name", "started_at_utc", "duration_ms",
            "status", "measurement",
        }
        for event in events
    ):
        raise ValueError("Unsafe or malformed tool event")
    count_by_tool = dict(sorted(Counter(event["name"] for event in events).items()))
    wall_ms = obs.get("wall_duration_ms")
    if not isinstance(wall_ms, (int, float)) or wall_ms <= 0:
        raise ValueError("Invalid measured review latency")
    trace_id = obs.get("trace_id")
    if trace_id is not None and (
        not isinstance(trace_id, str)
        or len(trace_id) != 32
        or any(c not in "0123456789abcdef" for c in trace_id)
    ):
        raise ValueError("Invalid OpenTelemetry trace ID")
    role_measures = obs.get("agent_measurements") or []
    if not isinstance(role_measures, list):
        raise ValueError("Invalid agent measurement records")
    allowed_roles = ("data_architect", "data_engineer", "verification_engineer")
    for item in role_measures:
        if (
            not isinstance(item, dict) or
            set(item) != {"role", "duration_ms", "status", "tokens", "measurement"}
            or item["role"] not in allowed_roles
            or item["measurement"] != "agent_middleware_monotonic"
            or item["status"] not in ("ok", "error")
            or not isinstance(item["duration_ms"], (int, float))
            or item["duration_ms"] < 0
            or not isinstance(item["tokens"], dict)
            or set(item["tokens"]) != {
                "input_token_count", "output_token_count", "reasoning_output_token_count",
            }
            or any(
                value is not None and (type(value) is not int or value < 0 or value > 10_000_000)
                for value in item["tokens"].values()
            )
        ):
            raise ValueError("Invalid measured role telemetry")
    if len(role_measures) > 3 or len({item["role"] for item in role_measures}) != len(role_measures):
        raise ValueError("Repeated agent telemetry")
    measured_roles = obs.get("individual_agent_wall_ms")
    if measured_roles is not None:
        if not isinstance(measured_roles, dict) or set(measured_roles) != set(allowed_roles):
            raise ValueError("Incomplete agent wall measurements")
        if {item["role"]: item["duration_ms"] for item in role_measures} != measured_roles:
            raise ValueError("Tampered measured role timings")
    model_tokens = obs.get("model_token_usage")
    if model_tokens is not None:
        if not isinstance(model_tokens, dict) or set(model_tokens) != {
            "input_token_count", "output_token_count"
        }:
            raise ValueError("Invalid model usage")
        for value in model_tokens.values():
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Invalid token count")
    if obs.get("estimated_model_cost") is not None:
        raise ValueError("Cannot report unpriced model usage as verified billing cost")
    attestation = manifest["deterministic_attestation"]
    if not all(attestation.get(key) for key in (
        "provenance_matched", "three_structured_agent_reports",
        "deterministic_reconciliation_confirmed",
    )):
        raise ValueError("Review is not provenance-verified")

    return {
        "schema_version": 1,
        "measurement_source": "real_foundry_run",
        "generated_at_utc": manifest["generated_at_utc"],
        "git_revision": manifest["git_revision"],
        "github_run_id": obs.get("github_run_id"),
        "model_deployment": manifest["model_deployment"],
        "source_sha256": manifest["provenance"]["source_sha256"],
        "wall_duration_ms": wall_ms,
        "tool_call_count": len(events),
        "tool_counts": count_by_tool,
        "events": events,
        "trace_id": trace_id,
        "otel_exporter_configured": bool(obs.get("otel_exporter_configured")),
        "model_token_usage": model_tokens,
        "estimated_model_cost": None,
        "individual_agent_wall_ms": measured_roles,
        "agent_measurements": role_measures,
        "disclaimer": "Raw tool parameters and prompts omitted. Agent timings from monotonic middleware and token counts only when returned by the SDK; billing cost is not estimated.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "agentic_review_runtime.json")
    parser.add_argument("--output", type=Path, default=ROOT / "public_agent_trace.json")
    args = parser.parse_args()
    manifest = json.loads(args.input.read_text(encoding="utf-8"))
    verify_manifest(manifest)
    snapshot = make_public_trace(manifest)
    args.output.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        "Recorded telemetry: "
        f"{snapshot['tool_call_count']} tool calls, "
        f"{snapshot['wall_duration_ms']} ms, "
        f"OTel exporter={snapshot['otel_exporter_configured']}"
    )


if __name__ == "__main__":
    main()
