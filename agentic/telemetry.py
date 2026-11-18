"""Privacy-safe, measured tool-call telemetry for read-only Foundry agents.

No prompts, tool arguments, raw CSV rows, or model-generated text are recorded.
The public view is derived from real measured events, never synthetic timings.
"""
from __future__ import annotations

import functools
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, TypeVar

F = TypeVar("F", bound=Callable[..., Any])
_active: "ToolRecorder | None" = None
_active_lock = threading.Lock()


class ToolRecorder:
    """Process-local collector: one bounded review run per GitHub worker process."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, name: str, started: str, elapsed_ms: float, status: str) -> None:
        with self._lock:
            self._events.append({
                "kind": "tool_call",
                "name": name,
                "started_at_utc": started,
                "duration_ms": round(elapsed_ms, 3),
                "status": status,
                "measurement": "runtime_clock",
            })

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(
                [dict(event) for event in self._events],
                key=lambda entry: entry["started_at_utc"],
            )


@contextmanager
def active_recorder(recorder: ToolRecorder) -> Iterator[None]:
    """Install a recorder only for the active bounded agent review."""
    global _active
    with _active_lock:
        if _active is not None:
            raise RuntimeError("Overlapping Foundry reviews are not supported")
        _active = recorder
    try:
        yield
    finally:
        with _active_lock:
            _active = None


def observed_tool(name: str) -> Callable[[F], F]:
    """Wrap a real tool call without changing its signature or return value."""

    def decorate(function: F) -> F:
        @functools.wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            started = datetime.now(timezone.utc).isoformat()
            tick = time.perf_counter_ns()
            status = "ok"
            # Agent Framework exports its own nested OTel spans when a provider
            # is configured. This extra span only records a stable tool name.
            try:
                from opentelemetry import trace
                tracer = trace.get_tracer("cloudfide.agentic.tools")
                with tracer.start_as_current_span(f"cloudfide.tool.{name}") as span:
                    span.set_attribute("tool.name", name)
                    span.set_attribute("tool.inputs_recorded", False)
                    span.set_attribute("tool.outputs_recorded", False)
                    try:
                        return function(*args, **kwargs)
                    except Exception:
                        status = "error"
                        span.set_attribute("tool.status", "error")
                        raise
            except ImportError:
                try:
                    return function(*args, **kwargs)
                except Exception:
                    status = "error"
                    raise
            finally:
                elapsed_ms = max(0.0, (time.perf_counter_ns() - tick) / 1_000_000)
                recorder = _active
                if recorder is not None:
                    recorder.add(name, started, elapsed_ms, status)
                    # Publish metadata only. Never send the raw arguments or result.
                    from .live_events import emit
                    emit("tool.completed", tool=name, duration_ms=round(elapsed_ms, 3), status=status)

        return wrapped  # type: ignore[return-value]

    return decorate
