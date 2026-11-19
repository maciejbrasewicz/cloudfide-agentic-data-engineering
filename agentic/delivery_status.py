"""Deterministic P5 controller for up to 3 verified, independent candidate rounds.

Never accepts a Foundry model's narrative. Reads only immutable source hashes,
actual P2/P5 candidate files and P3 independent sandbox receipts. No untrusted
candidate code is imported or executed by the final controller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .candidate_intake import verify_and_stage_candidate


ROUNDS = (
    ("p2-engineer-candidate-pending-sandbox", "p3-independent-sandbox-validation"),
    ("p5-engineer-rework-r2", "p5-sandbox-r2-validation"),
    ("p5-engineer-rework-r3", "p5-sandbox-r3-validation"),
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object: " + str(path))
    return data


def evaluate_delivery_rounds(artifacts: Path, original: Path, scratch: Path) -> dict:
    history: list[dict] = []
    first_missing_round = 0
    prior_admission: dict | None = None
    prior_verification: bytes | None = None
    for number, (candidate_label, sandbox_label) in enumerate(ROUNDS, 1):
        candidate = artifacts / candidate_label
        sandbox = artifacts / sandbox_label
        if not candidate.is_dir() or not sandbox.is_dir():
            first_missing_round = number
            break
        receipt_raw = (sandbox / "verification.json").read_bytes()
        receipt = json.loads(receipt_raw.decode("utf-8"))
        admission = _json(sandbox / "admission.json")
        gate = _json(candidate / "engineer_gate.json")
        request = _json(candidate / "validation_request.json")
        if gate.get("status") != "CANDIDATE_READY_FOR_SANDBOX" or gate.get("failures"):
            raise ValueError("Unapproved candidate from round " + str(number))
        candidate_workspace = scratch / ("round-" + str(number))
        fresh = verify_and_stage_candidate(
            archive_path=candidate / "candidate_bundle.zip",
            engineer_gate=gate, validation_request=request,
            original_checkout=original, destination=candidate_workspace,
        )
        if admission != fresh:
            raise ValueError("Independent sandbox admission differs from candidate SHA")
        if number > 1:
            lineage = _json(candidate / "rework_lineage.json")
            earlier_files = {
                entry["path"]: entry["sha256"] for entry in prior_admission["files"]
            } if prior_admission else {}
            next_files = {entry["path"]: entry["sha256"] for entry in fresh["files"]}
            if (
                lineage.get("iteration") != number
                or lineage.get("previous_file_hashes") != earlier_files
                or lineage.get("current_file_hashes") != next_files
                or not lineage.get("actual_change")
                or lineage.get("previous_p3_verdict_sha256") != sha(prior_verification or b"")
            ):
                raise ValueError("Rework candidate has invalid failure-to-fix provenance")
        status = receipt.get("status")
        if status not in {"PASSED", "FAILED"}:
            raise ValueError("P3 returned an unknown validation status")
        if receipt.get("source") != "independent_p3_stdlib_oracle":
            raise ValueError("P3 verdict not produced by trusted oracle")
        if status == "PASSED" and (
            receipt.get("reconciliation") != "passed"
            or receipt.get("sandbox_test_exit_code") != 0
            or receipt.get("sandbox_pipeline_exit_code") != 0
            or receipt.get("source_sha256") != fresh["protected_hashes"]["sales.csv"]
            or len(receipt.get("regions", {})) != 5
        ):
            raise ValueError("False P3 PASS contradicts independent source facts")
        history.append({
            "iteration": number,
            "candidate_artifact": candidate_label,
            "validation_artifact": sandbox_label,
            "candidate_status": status,
            "candidate_hashes": fresh["files"],
            "verdict_sha256": sha(receipt_raw),
            "failure": receipt.get("failure") if status == "FAILED" else None,
        })
        prior_admission, prior_verification = fresh, receipt_raw
        if status == "PASSED":
            return {
                "schema_version": 1, "status": "WAITING_VERIFIER",
                "accepted_for_verification_iteration": number,
                "iterations_used": number, "max_iterations": len(ROUNDS),
                "history": history,
                "approval": "NOT_APPROVED_FOR_PR_OR_MERGE",
            }
    if first_missing_round:
        return {
            "schema_version": 1, "status": "INCOMPLETE",
            "accepted_for_verification_iteration": None,
            "iterations_used": len(history), "max_iterations": len(ROUNDS),
            "history": history,
            "failure": "Missing candidate or sandbox receipt at round " + str(first_missing_round),
            "approval": "NOT_APPROVED_FOR_PR_OR_MERGE",
        }
    return {
        "schema_version": 1, "status": "REJECTED",
        "accepted_for_verification_iteration": None,
        "iterations_used": len(history), "max_iterations": len(ROUNDS),
        "history": history,
        "failure": "All three real independent candidate validations failed",
        "approval": "NOT_APPROVED_FOR_PR_OR_MERGE",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic bounded P5 control gate")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="cloudfide-p5-state-") as temp:
        try:
            outcome = evaluate_delivery_rounds(
                args.artifacts, args.original, Path(temp),
            )
        except (ValueError, KeyError, FileNotFoundError) as exc:
            outcome = {
                "schema_version": 1, "status": "INFRA_FAILURE",
                "accepted_for_verification_iteration": None,
                "iterations_used": 0, "max_iterations": len(ROUNDS),
                "history": [], "failure": str(exc),
                "approval": "NOT_APPROVED_FOR_PR_OR_MERGE",
            }

    outcome["github_run_id"] = os.environ.get("GITHUB_RUN_ID")
    outcome["base_commit_sha"] = os.environ.get("GITHUB_SHA")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "run_state.json"
    candidate = path.with_suffix(".tmp")
    candidate.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    candidate.replace(path)
    (args.output_dir / "iteration_history.json").write_text(
        json.dumps(outcome["history"], indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "status": outcome["status"], "iterations_used": outcome["iterations_used"],
        "selected": outcome["accepted_for_verification_iteration"],
        "failure": outcome.get("failure"),
    }))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write(
                "## Autonomous Data Engineering — deterministic P5 state\n\n"
                + "**" + outcome["status"] + "**"
                + "; rounds used: " + str(outcome["iterations_used"]) + "\n\n"
            )
    if outcome["status"] in {"INCOMPLETE", "INFRA_FAILURE"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
