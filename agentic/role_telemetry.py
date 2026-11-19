"""Privacy-safe real elapsed time per Foundry agent invocation.

No prompts, generated code, task text, tool arguments, client secrets, or
estimated prices are recorded. Unknown token usage remains null, not guessed.
"""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

KNOWN_ROLES = frozenset({
    "data_architect", "data_engineer", "verification_engineer",
    "data_engineer_rework_2", "data_engineer_rework_3",
})


@contextmanager
def measure_role(
    *, role: str, output_dir: Path, model_deployment: str,
    tool_call_count: Callable[[], int],
) -> Iterator[None]:
    """Measure ACTUAL agent.run plus tool calls; do not infer model token cost."""
    if role not in KNOWN_ROLES:
        raise ValueError("Unknown telemetry role")
    begin = time.perf_counter_ns()
    started = datetime.now(timezone.utc).isoformat()
    status = "success"
    try:
        yield
    except BaseException:
        status = "error"
        raise
    finally:
        elapsed_ms = round(max(0, time.perf_counter_ns() - begin) / 1_000_000, 3)
        payload = {
            "schema_version": 1,
            "source": "measured_role_monotonic_clock",
            "role": role,
            "status": status,
            "started_at_utc": started,
            "duration_ms": elapsed_ms,
            "tool_call_count": tool_call_count(),
            "model_deployment": model_deployment,
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_base_sha": os.environ.get("GITHUB_SHA"),
            "input_tokens": None,
            "output_tokens": None,
            "estimated_cost": None,
            "privacy": "no_prompts_no_arguments_no_generated_code",
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = output_dir / "role_telemetry.json"
        temp = filename.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temp.replace(filename)
