"""P6 workflow permissions and CI boundary must stay independently reviewable."""
from __future__ import annotations

from pathlib import Path

import pytest


def _jobs(filename: str) -> dict:
    yaml = pytest.importorskip("yaml")
    root = Path(__file__).resolve().parents[1]
    return yaml.safe_load((root / ".github/workflows" / filename).read_text(encoding="utf-8"))["jobs"]


def test_publisher_runs_after_actual_adversarial_job_with_no_azure_credentials():
    jobs = _jobs("engineer-e2e.yml")
    publisher = jobs["publish-draft-pr"]
    assert set(publisher["needs"]) == {"p5-state", "verifier", "adversarial"}
    assert publisher["permissions"] == {
        "contents": "write", "pull-requests": "write", "actions": "write",
    }
    assert "needs.adversarial.result == 'success'" in publisher["if"]
    assert all("azure/login" not in str(step) for step in publisher["steps"])
    assert all("CLOUDFIDE_TASK_SPEC" not in str(step) for step in publisher["steps"])
    assert "gh pr create" in str(publisher["steps"])
    assert "--draft" in str(publisher["steps"])
    assert "candidate-ci.yml/dispatches" in str(publisher["steps"])


def test_candidate_ci_runs_generated_python_only_in_no_network_container():
    jobs = _jobs("candidate-ci.yml")
    assert set(jobs) == {"validate"}
    job = jobs["validate"]
    assert job["permissions"] == {"contents": "read", "statuses": "write"}
    assert "refs/heads/main" in job["if"]
    assert all("azure/login" not in str(step) for step in job["steps"])
    text = str(job["steps"])
    assert "agentic.candidate_branch_ci" in text
    assert "--network none" in text
    assert "--read-only" in text
    assert "--cap-drop ALL" in text
    assert "agentic.p3_oracle" in text
    assert "statuses/$EXPECTED_SHA" in text
