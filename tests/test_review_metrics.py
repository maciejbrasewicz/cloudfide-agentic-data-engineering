"""No invented token/cost/role timings; only actual middleware and provider counters."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from agentic.review_metrics import ReviewMetrics, usage_details


def test_usage_details_preserve_actual_sdk_counters():
    output = SimpleNamespace(usage_details=SimpleNamespace(
        input_token_count=150,output_token_count=60,reasoning_output_token_count=11
    ))
    assert usage_details(output) == {
        "input_token_count": 150,
        "output_token_count": 60,
        "reasoning_output_token_count": 11,
    }


def test_usage_is_unknown_without_explicit_provider_metadata():
    assert all(value is None for value in usage_details(SimpleNamespace()).values())
    stats = ReviewMetrics()
    stats.record("data_architect", 11.5, SimpleNamespace())
    summary = stats.summary()
    assert summary["individual_agent_wall_ms"] is None
    assert summary["model_token_usage"] is None
    assert summary["estimated_model_cost"] is None
    assert summary["agent_measurements"][0]["duration_ms"] == 11.5


def test_three_true_agent_measurements_and_tokens_sum_only_complete_providers():
    report = ReviewMetrics()
    for role,elapsed,in_t,out_t in [
        ("data_architect", 1100.2, 100, 25),
        ("data_engineer", 2100.5, 140, 35),
        ("verification_engineer", 3100.1, 210, 40)
    ]:
        report.record(role,elapsed,SimpleNamespace(usage_details={
            "input_token_count":in_t,"output_token_count":out_t,
            "reasoning_output_token_count":None
        }))
    result=report.summary()
    assert result["individual_agent_wall_ms"]["data_engineer"]==2100.5
    assert result["model_token_usage"]=={"input_token_count":450,"output_token_count":100}
    assert result["estimated_model_cost"] is None


def test_missing_provider_usage_does_not_infer_token_total():
    report=ReviewMetrics()
    for i,role in enumerate(("data_architect","data_engineer","verification_engineer")):
        metadata={"input_token_count":20,"output_token_count":10} if i<2 else {}
        report.record(role,5.5,SimpleNamespace(usage_details=metadata))
    assert report.summary()["model_token_usage"] is None


@pytest.mark.parametrize("elapsed",[-1,float("nan"),float("inf")])
def test_invalid_elapsed_time_rejected(elapsed):
    with pytest.raises(ValueError):
        ReviewMetrics().record("data_architect",elapsed)


def test_duplicate_role_samples_rejected():
    report=ReviewMetrics()
    report.record("data_architect",100)
    with pytest.raises(ValueError):
        report.record("data_architect",200)
