"""The reviewer smoke may not pin 'latest' to historical successful run #44485096373."""

from copy import deepcopy

import pytest

from scripts.verify_live_delivery_feed import validate_live_delivery

REPO = "https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering"
SOURCE_SHA = "a" * 40
CANDIDATE_SHA = "b" * 40
RUN_ID = 44501856719
PHASE_NAMES = ("architect", "engineer", "p5-state", "verifier", "adversarial", "publish-draft-pr")


def evidence():
    return {
        "available": True,
        "source": "public_github_actions",
        "run": {
            "id": RUN_ID,
            "url": f"{REPO}/actions/runs/{RUN_ID}",
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "commit_sha": SOURCE_SHA,
        },
        "phases": [
            {"id": name, "status": "completed", "conclusion": "success"}
            for name in PHASE_NAMES
        ],
        "publication": {
            "status": "verified_draft_awaiting_human",
            "pullRequest": {
                "number": 35,
                "url": f"{REPO}/pull/35",
                "draft": True,
                "headSha": CANDIDATE_SHA,
            },
            "exactCi": {
                "context": "agentic-delivery/isolated-candidate-ci",
                "state": "success",
            },
        },
    }


def test_verified_live_run_has_real_p4_draft_and_exact_sha_proof():
    assert "verified_draft_awaiting_human" in validate_live_delivery(evidence())


def test_prior_false_green_run_is_allowed_but_cannot_be_presented_as_verified():
    doc = evidence()
    for phase in doc["phases"]:
        if phase["id"] in {"verifier", "adversarial", "publish-draft-pr"}:
            phase["conclusion"] = "skipped"
    doc["publication"] = {"status": "not_yet_verified", "pullRequest": None, "exactCi": None}
    assert "not_yet_verified" in validate_live_delivery(doc)
    doc["publication"] = evidence()["publication"]
    with pytest.raises(ValueError, match="Verified claim without successful verifier"):
        validate_live_delivery(doc)


def test_newest_running_job_is_not_a_ci_smoke_failure():
    doc = evidence()
    doc["run"]["status"] = "in_progress"
    doc["run"]["conclusion"] = None
    doc["publication"] = {"status": "not_yet_verified", "pullRequest": None, "exactCi": None}
    assert "in_progress" in validate_live_delivery(doc)


def test_real_draft_without_green_exact_sha_is_not_verified():
    doc = evidence()
    doc["publication"]["exactCi"]["state"] = "pending"
    with pytest.raises(ValueError, match="independent exact-SHA CI"):
        validate_live_delivery(doc)
    doc["publication"]["status"] = "draft_ci_not_confirmed"
    assert "draft_ci_not_confirmed" in validate_live_delivery(doc)


def test_reject_mismatching_run_url_and_fake_sha():
    doc = evidence()
    bad = deepcopy(doc)
    bad["run"]["url"] = f"{REPO}/actions/runs/999"
    with pytest.raises(ValueError, match="Non-canonical run"):
        validate_live_delivery(bad)
    bad = deepcopy(doc)
    bad["publication"]["pullRequest"]["headSha"] = "unverified"
    with pytest.raises(ValueError, match="candidate SHA"):
        validate_live_delivery(bad)


def test_no_false_acceptance_if_public_evidence_unavailable():
    doc = evidence()
    doc["available"] = False
    with pytest.raises(ValueError, match="unavailable"):
        validate_live_delivery(doc)
