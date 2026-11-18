"""Runtime measurements for individual Foundry agent invocations.

Agent Framework middleware measures actual elapsed wall time. Provider token
usage is included only when the SDK returns explicit UsageDetails counters.
No tokens are inferred from text length and no pricing is estimated.
"""
from __future__ import annotations

import math
from typing import Any


ROLES = ("data_architect", "data_engineer", "verification_engineer")
COUNTERS = ("input_token_count", "output_token_count", "reasoning_output_token_count")


def _counter(usage: Any, key: str) -> int | None:
    if usage is None:
        return None
    value = usage.get(key) if isinstance(usage, dict) else getattr(usage, key, None)
    if type(value) is int and 0 <= value <= 10_000_000:
        return value
    return None


def usage_details(response: Any) -> dict[str, int | None]:
    """Use only explicit SDK-returned counters; never estimate them."""
    details = getattr(response, "usage_details", None)
    if details is None and isinstance(response, dict):
        details = response.get("usage_details")
    return {key: _counter(details, key) for key in COUNTERS}


class ReviewMetrics:
    def __init__(self) -> None:
        self._records: dict[str, dict] = {}

    def record(self, role: str, elapsed_ms: float, response: Any = None, status: str = "ok") -> None:
        if role not in ROLES or role in self._records:
            raise ValueError("Unrecognized or repeated reviewer role")
        if not isinstance(elapsed_ms, (int, float)) or not math.isfinite(elapsed_ms) or elapsed_ms < 0:
            raise ValueError("Invalid actual wall-clock measurement")
        if status not in ("ok", "error"):
            raise ValueError("Invalid agent execution status")
        self._records[role] = {
            "role": role,
            "duration_ms": round(elapsed_ms, 3),
            "status": status,
            "tokens": usage_details(response),
            "measurement": "agent_middleware_monotonic",
        }

    def snapshot(self) -> list[dict]:
        return [dict(self._records[role]) for role in ROLES if role in self._records]

    def summary(self) -> dict:
        measurements = self.snapshot()
        all_roles = len(measurements) == 3 and all(e["status"] == "ok" for e in measurements)
        token_fields = {}
        for field in ("input_token_count", "output_token_count"):
            values = [item["tokens"][field] for item in measurements]
            token_fields[field] = sum(values) if all_roles and all(v is not None for v in values) else None
        return {
            "individual_agent_wall_ms": (
                {item["role"]: item["duration_ms"] for item in measurements} if all_roles else None
            ),
            "model_token_usage": (
                token_fields if any(v is not None for v in token_fields.values()) else None
            ),
            "agent_measurements": measurements,
            "estimated_model_cost": None,
            "pricing_status": "no_verified_deployment_billing_rates",
        }
