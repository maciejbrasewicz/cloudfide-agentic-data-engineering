"""Validate truthful, dynamic production evidence without assuming a historical run stays latest.

The production portal tracks the newest GitHub Actions delivery. A new run may be
queued, executing, failed or completed without P4; those are not smoke-test
failures. Claiming verified delivery without P4 and exact-SHA CI IS a failure.
This validator never reads Railway credentials or starts a Foundry execution.
"""

import json
import re
import sys
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}")
PHASES = ("architect", "engineer", "p5-state", "verifier", "adversarial", "publish-draft-pr")
PUBLICATION_STATES = {
    "not_yet_verified", "evidence_unavailable", "draft_ci_not_confirmed",
    "verified_draft_awaiting_human",
}
REPO = "https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_live_delivery(document: dict) -> str:
    """Return a privacy-safe status line, rejecting forged verified states."""
    require(isinstance(document, dict) and document.get("available") is True,
            "Production GitHub evidence is unavailable")
    require(document.get("source") == "public_github_actions", "Unexpected evidence source")
    run = document.get("run")
    require(isinstance(run, dict), "Missing run")
    run_id = run.get("id")
    require(type(run_id) is int and run_id > 0, "Invalid GitHub run ID")
    require(run.get("url") == f"{REPO}/actions/runs/{run_id}", "Non-canonical run URL")
    require(run.get("event") in {"push", "workflow_dispatch"}, "Unexpected run trigger")
    require(run.get("status") in {"queued", "in_progress", "completed", "pending", "waiting"},
            "Invalid execution status")
    require(isinstance(run.get("commit_sha"), str) and SHA.fullmatch(run["commit_sha"]),
            "Missing trusted-main source SHA")

    phases = document.get("phases")
    require(isinstance(phases, list), "Missing phase evidence")
    by_id = {p.get("id"): p for p in phases if isinstance(p, dict)}
    require(all(name in by_id for name in PHASES), "Delivery phase inventory incomplete")

    publication = document.get("publication")
    require(isinstance(publication, dict), "Missing publication evidence")
    status = publication.get("status")
    require(status in PUBLICATION_STATES, "Unexpected publication state")

    if status == "verified_draft_awaiting_human":
        require(run.get("status") == "completed" and run.get("conclusion") == "success",
                "Verified claim without successful terminal workflow")
        for phase in PHASES:
            require(by_id[phase].get("conclusion") == "success",
                    f"Verified claim without successful {phase}")
        pr = publication.get("pullRequest")
        ci = publication.get("exactCi")
        require(isinstance(pr, dict) and type(pr.get("number")) is int
                and pr["number"] > 0 and pr.get("draft") is True,
                "Verified claim without a real draft PR")
        require(pr.get("url") == f"{REPO}/pull/{pr['number']}", "Non-canonical draft PR URL")
        require(isinstance(pr.get("headSha"), str) and SHA.fullmatch(pr["headSha"]),
                "Verified claim without candidate SHA")
        require(isinstance(ci, dict) and ci.get("context") == "agentic-delivery/isolated-candidate-ci"
                and ci.get("state") == "success", "Verified claim without independent exact-SHA CI")

    return f"Live GitHub run {run_id}: {run['status']}; publication={status}"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_live_delivery_feed.py LATEST_JSON_PATH")
    try:
        document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        print(validate_live_delivery(document))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Production live delivery evidence rejected: {exc}") from None


if __name__ == "__main__":
    main()
