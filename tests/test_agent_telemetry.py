"""Real tool-call telemetry is measured, bounded and privacy-safe."""
import inspect
import json
import time

import pytest

from agentic.telemetry import ToolRecorder, active_recorder, observed_tool


def test_successful_tool_call_keeps_signature_and_only_records_metadata():
    @observed_tool("example")
    def example(secret: str, count: int = 1) -> str:
        """Return a private result."""
        time.sleep(0.002)
        return secret * count

    assert list(inspect.signature(example).parameters) == ["secret", "count"]
    recorder = ToolRecorder()
    with active_recorder(recorder):
        assert example("PRIVATE_VALUE", 2) == "PRIVATE_VALUEPRIVATE_VALUE"
    captured = recorder.snapshot()
    assert len(captured) == 1
    assert captured[0]["name"] == "example"
    assert captured[0]["status"] == "ok"
    assert captured[0]["duration_ms"] >= 0
    assert "PRIVATE_VALUE" not in json.dumps(captured)
    assert "args" not in captured[0]
    assert "result" not in captured[0]


def test_exception_is_preserved_and_event_is_marked_failed():
    @observed_tool("failure")
    def crash() -> None:
        raise ValueError("private failure detail")

    recorder = ToolRecorder()
    with active_recorder(recorder):
        with pytest.raises(ValueError, match="private failure"):
            crash()
    events = recorder.snapshot()
    assert len(events) == 1
    assert events[0]["status"] == "error"
    assert "private failure detail" not in json.dumps(events)


def test_nested_review_recorder_is_rejected():
    outer, inner = ToolRecorder(), ToolRecorder()
    with active_recorder(outer):
        with pytest.raises(RuntimeError, match="Overlapping"):
            with active_recorder(inner):
                pass
    with active_recorder(inner):
        pass


def test_no_collector_means_no_persistent_recording():
    @observed_tool("without_recorder")
    def increment(value: int) -> int:
        return value + 1
    assert increment(4) == 5
