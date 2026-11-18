"""Lightweight event gateway contract; no LLM data or credentials are exported.

This is the transport used by OIDC-authenticated GitHub Actions runners. Its
strict field allowlist prevents tool parameters and prompt content from leaking.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_TOOL_NAMES = {
    "profile_source", "inspect_orders", "read_project_file",
    "check_quality", "inspect_approved_policy", "inspect_reconciliation",
}
_ROLES = {"data_architect", "data_engineer", "verification_engineer"}
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_cached_oidc: tuple[str, float] | None = None


def enabled() -> bool:
    rid = os.environ.get("LIVE_REQUEST_ID", "")
    return (
        os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and bool(_UUID.fullmatch(rid))
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
        and os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "") != ""
        and os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "") != ""
        and os.environ.get("REVIEW_LIVE_SINK_URL", "").startswith("https://")
    )


def _oidc_token() -> str:
    global _cached_oidc
    now = __import__("time").time()
    if _cached_oidc and _cached_oidc[1] > now + 45:
        return _cached_oidc[0]
    audience = os.environ["REVIEW_LIVE_SINK_URL"].rstrip("/") + "/api/live/events"
    requested = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    sep = "&" if "?" in requested else "?"
    request = Request(
        requested + sep + urlencode({"audience": audience}),
        headers={"Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]},
    )
    with urlopen(request, timeout=4) as response:
        token = json.load(response)["value"]
    # Tokens are refreshed frequently; never write them to artifacts or logs.
    _cached_oidc = (token, now + 180)
    return token


def sanitize_event(kind: str, payload: dict[str, Any]) -> dict:
    allowed = {
        "workflow.started": set(),
        "tool.completed": {"tool", "duration_ms", "status"},
        "agent.completed": {"role", "summary", "findings"},
        "workflow.completed": {"total_ms", "tool_count"},
        "workflow.failed": {"phase"},
    }
    if kind not in allowed or set(payload) != allowed[kind]:
        raise ValueError("Unsupported live event structure")
    if kind == "tool.completed" and (
        payload["tool"] not in _TOOL_NAMES or
        payload["status"] not in ("ok", "error") or
        not isinstance(payload["duration_ms"], (int, float)) or
        not 0 <= payload["duration_ms"] <= 120_000
    ):
        raise ValueError("Invalid tool event")
    if kind == "agent.completed" and (
        payload["role"] not in _ROLES or
        not isinstance(payload["summary"], str) or
        not 10 <= len(payload["summary"]) <= 1000 or
        not isinstance(payload["findings"], int) or
        not 0 <= payload["findings"] <= 12
    ):
        raise ValueError("Invalid agent event")
    if kind == "workflow.completed" and (
        not isinstance(payload["total_ms"], (int, float)) or
        payload["total_ms"] <= 0 or
        not isinstance(payload["tool_count"], int) or payload["tool_count"] < 0
    ):
        raise ValueError("Invalid workflow completion event")
    if kind == "workflow.failed" and payload["phase"] not in (
        "foundry_review", "schema_validation", "provenance_gate"
    ):
        raise ValueError("Invalid failure phase")
    return {
        "type": kind,
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "classification": "measured_metadata" if kind != "agent.completed" else "untrusted_model_output",
    }


def emit(kind: str, **payload: Any) -> None:
    """Best-effort low-volume event delivery; never blocks the correctness gate."""
    if not enabled():
        return
    try:
        event = sanitize_event(kind, payload)
        body = json.dumps({
            "request_id": os.environ["LIVE_REQUEST_ID"],
            "event": event,
        }, ensure_ascii=False).encode("utf-8")
        request = Request(
            os.environ["REVIEW_LIVE_SINK_URL"].rstrip("/") + "/api/live/events",
            data=body, method="POST",
            headers={
                "Authorization": "Bearer " + _oidc_token(),
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=4) as response:
            if response.status not in (200, 202, 204):
                raise OSError("Event sink rejected event")
    except (OSError, ValueError, KeyError, TypeError, TimeoutError, Exception):
        # Telemetry cannot alter or certify the ETL. Secrets and raw errors are never logged.
        pass
