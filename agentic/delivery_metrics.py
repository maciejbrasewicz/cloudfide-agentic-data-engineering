"""Privacy-safe operational telemetry for full 3-agent Foundry delivery.

Derives data from actual GitHub Actions job timestamps and trusted P5/P4/P6
receipts. Never guesses token usage, cost, OpenTelemetry trace IDs, or
completion of a separate asynchronously triggered candidate CI workflow.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

ALLOWED_STAGES = {
    "architect", "engineer", "sandbox-validate",
    "rework-r2", "sandbox-rework-r2", "rework-r3",
    "sandbox-rework-r3", "p5-state", "verifier",
    "adversarial", "publish-draft-pr", "policy-review",
    "delivery-telemetry",
}
ACTUAL_ROLES = (
    ("p2-architect-receipt", "data_architect"),
    ("p2-engineer-candidate-pending-sandbox", "data_engineer"),
    ("p5-engineer-rework-r2", "data_engineer_rework_2"),
    ("p5-engineer-rework-r3", "data_engineer_rework_3"),
    ("p4-verifier-evidence", "verification_engineer"),
)


class DeliveryTelemetryError(ValueError):
    """Untrusted job metadata or receipt cannot prove execution."""


def _json_or_none(path: Path):
    if not path.is_file():
        return None
    if path.is_symlink() or path.stat().st_size > 150_000:
        raise DeliveryTelemetryError("Unsafe or oversized telemetry input")
    return json.loads(path.read_text(encoding="utf-8"))


def _duration_ms(job: dict) -> float | None:
    start, end = job.get("started_at"), job.get("completed_at")
    if not start or not end:
        return None
    try:
        a = datetime.fromisoformat(start.replace("Z", "+00:00"))
        b = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return round(max(0, (b-a).total_seconds() * 1000), 3)
    except ValueError as exc:
        raise DeliveryTelemetryError("Invalid GitHub job timestamp") from exc


def create_delivery_metrics(*, jobs_payload: dict, artifacts: Path,
                            run_id: str, base_sha: str) -> dict:
    if not run_id.isdecimal() or len(base_sha) != 40 or not all(c in "0123456789abcdef" for c in base_sha):
        raise DeliveryTelemetryError("Invalid run provenance")
    jobs = jobs_payload.get("jobs")
    if not isinstance(jobs, list):
        raise DeliveryTelemetryError("Missing real GitHub Actions jobs")
    rows = []
    for job in jobs:
        name = job.get("name")
        if not isinstance(name, str) or not isinstance(job.get("id"), int):
            raise DeliveryTelemetryError("Job IDs or names missing")
        duration = _duration_ms(job)
        rows.append({
            "job_id": job["id"],
            "name": name[:180],
            "status": job.get("status"),
            "conclusion": job.get("conclusion"),
            "duration_ms": duration,
            "measurement": "github_actions_job_started_and_completed_at",
        })
    sources = {}
    for artifact_name, role in ACTUAL_ROLES:
        raw = _json_or_none(artifacts / artifact_name / "role_telemetry.json")
        if raw is None:
            sources[role] = None
            continue
        if (raw.get("schema_version") != 1
                or raw.get("source") != "measured_role_monotonic_clock"
                or raw.get("role") != role
                or raw.get("github_run_id") != run_id
                or raw.get("github_base_sha") != base_sha
                or raw.get("status") not in {"success", "error"}
                or not isinstance(raw.get("duration_ms"), (int, float))
                or raw["duration_ms"] < 0
                or not isinstance(raw.get("tool_call_count"), int)
                or raw["tool_call_count"] < 0):
            raise DeliveryTelemetryError("Forged or stale role observation: " + role)
        sources[role] = {
            "status": raw["status"],
            "duration_ms": raw["duration_ms"],
            "tool_call_count": raw["tool_call_count"],
            "measurement": raw["source"],
            "input_tokens": None,
            "output_tokens": None,
            "estimated_cost": None,
        }
    state = _json_or_none(artifacts / "p5-bounded-run-state/run_state.json")
    if state is not None and (state.get("github_run_id") != run_id or state.get("base_commit_sha") != base_sha):
        raise DeliveryTelemetryError("P5 run-state SHA mismatch")
    p4 = _json_or_none(artifacts / "p4-independent-adversarial-validation/verifier_verdict.json")
    if p4 is not None and (
        p4.get("source") != "independent_p4_dual_sandbox_verification"
        or p4.get("status") not in {"PASSED", "REWORK_REQUIRED", "WEAK_VERIFIER_TEST"}
    ):
        raise DeliveryTelemetryError("Unrecognized Verifier receipt")
    publish = _json_or_none(artifacts / "p6-publication-receipt/agentic_delivery_manifest.json")
    if publish is not None and (publish.get("source_run_id") != run_id
        or publish.get("base_commit_sha") != base_sha):
        raise DeliveryTelemetryError("Publisher receipt belongs to another source run")
    return {
        "schema_version": 1,
        "source": "real_github_jobs_and_independent_source_receipts",
        "github_run_id": run_id,
        "base_commit_sha": base_sha,
        "jobs": rows,
        "agent_measurements": sources,
        "p5": ({
            "status": state["status"], "iterations_used": state["iterations_used"],
            "selected_iteration": state["accepted_for_verification_iteration"],
            "history": [{"iteration": x["iteration"], "status": x["candidate_status"],
                         "verdict_sha256": x["verdict_sha256"]}
                        for x in state.get("history", [])],
        } if state is not None else None),
        "p4": ({
            "status": p4["status"],
            "mutation_detected": p4.get("negative_mutation_test_exit_code", 0) != 0,
            "test_sha256": p4.get("verifier_test_sha256"),
        } if p4 is not None else None),
        "publisher": ({
            "status": publish["status"], "candidate_manifest_sha256": publish["candidate_manifest_sha256"],
            "later_candidate_ci_status": "NOT_CHECKED_BY_SOURCE_RUN",
        } if publish is not None else None),
        "otel_trace_id": None,
        "model_token_usage": None,
        "model_cost": None,
        "telemetry_limitation": "role duration is observed for new runs only; job wall time includes setup; no token cost without SDK usage receipts",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jobs", required=True, type=Path)
    p.add_argument("--artifacts", required=True, type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--base-sha", required=True)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    result = create_delivery_metrics(
        jobs_payload=json.loads(a.jobs.read_text(encoding="utf-8")),
        artifacts=a.artifacts, run_id=a.run_id, base_sha=a.base_sha,
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "measured_jobs": len(result["jobs"]),
        "actual_role_durations": sum(x is not None for x in result["agent_measurements"].values()),
        "p5_status": result["p5"]["status"] if result["p5"] else None,
        "p4_status": result["p4"]["status"] if result["p4"] else None,
        "model_cost": None,
    }))


if __name__ == "__main__":
    main()
