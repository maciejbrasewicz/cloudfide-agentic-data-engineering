"""Trusted P6 publication admission: no candidate Python execution, no Azure.

Stage only candidate source proven by real P3 and P4 independent receipts.
Published output is always a human-reviewed draft PR, never an auto-merge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from .candidate_intake import verify_and_stage_candidate
from .delivery_status import ROUNDS
from .p3_oracle import compare_output
from .patch_policy import is_candidate_path
from .verifier_gate import TEST_PATH, candidate_manifest_digest, validate_adversarial_test


class DraftPublicationError(ValueError):
    """Final independent evidence is missing or inconsistent."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 200_000:
        raise DraftPublicationError("Missing or oversized evidence: " + path.name)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DraftPublicationError("Expected JSON evidence object")
    return value


def prepare_publication(
    *, artifacts: Path, original: Path, destination: Path,
    run_id: str, base_sha: str,
) -> dict:
    if not run_id.isdecimal() or not 1 <= len(run_id) <= 30:
        raise DraftPublicationError("Invalid source run identifier")
    if len(base_sha) != 40 or any(c not in "0123456789abcdef" for c in base_sha):
        raise DraftPublicationError("Invalid base commit fingerprint")
    state = _read(artifacts / "p5-bounded-run-state/run_state.json")
    if state.get("status") != "WAITING_VERIFIER":
        raise DraftPublicationError("P5 did not select a successful candidate")
    if str(state.get("github_run_id")) != run_id or state.get("base_commit_sha") != base_sha:
        raise DraftPublicationError("P5 source run ID or SHA mismatch")
    iteration = state.get("accepted_for_verification_iteration")
    if type(iteration) is not int or not 1 <= iteration <= 3:
        raise DraftPublicationError("Missing selected candidate iteration")

    p4_dir = artifacts / "p4-independent-adversarial-validation"
    verdict = _read(p4_dir / "verifier_verdict.json")
    admission = _read(p4_dir / "admission.json")
    positive = _read(p4_dir / "positive_finance_oracle.json")
    if (
        verdict.get("status") != "PASSED"
        or verdict.get("next_stage") != "P6_DRAFT_PR_REVIEW"
        or verdict.get("falsification_sensitivity") != "PASSED"
        or verdict.get("positive_test_exit_code") != 0
        or verdict.get("positive_pipeline_exit_code") != 0
        or verdict.get("negative_mutation_test_exit_code") == 0
        or verdict.get("iteration") != iteration
        or verdict.get("failures")
    ):
        raise DraftPublicationError("Real P4 dual-sandbox Verification Engineer did not pass")
    positive_bytes = (p4_dir / "positive_finance_oracle.json").read_bytes()
    if (
        positive.get("status") != "PASSED"
        or positive.get("reconciliation") != "passed"
        or positive.get("sandbox_test_exit_code") != 0
        or positive.get("sandbox_pipeline_exit_code") != 0
        or verdict.get("positive_oracle_sha256") != _sha(positive_bytes)
    ):
        raise DraftPublicationError("Positive Verifier oracle receipt cannot be trusted")

    candidate_label, sandbox_label = ROUNDS[iteration - 1]
    candidate_dir = artifacts / candidate_label
    p3 = _read(artifacts / sandbox_label / "verification.json")
    if p3.get("status") != "PASSED" or p3.get("reconciliation") != "passed":
        raise DraftPublicationError("Candidate did not pass the original P3 oracle")
    if p3.get("source_sha256") != _sha((original / "sales.csv").read_bytes()):
        raise DraftPublicationError("Original source changed since P3")

    with tempfile.TemporaryDirectory(prefix="cloudfide-p6-") as temporary:
        source_dir = Path(temporary) / "candidate"
        staged = verify_and_stage_candidate(
            archive_path=candidate_dir / "candidate_bundle.zip",
            engineer_gate=_read(candidate_dir / "engineer_gate.json"),
            validation_request=_read(candidate_dir / "validation_request.json"),
            original_checkout=original, destination=source_dir,
        )
        candidate_sha = candidate_manifest_digest(staged["files"])
        if admission.get("candidate_manifest_sha256") != candidate_sha or verdict.get("candidate_manifest_sha256") != candidate_sha:
            raise DraftPublicationError("P4 cited another candidate manifest")
        source_hashes = staged["protected_hashes"]
        if admission.get("original_test_sha256") != source_hashes["test_virtual_column.py"]:
            raise DraftPublicationError("Employer original test fingerprint changed")

        test_file = artifacts / "p4-verifier-evidence" / TEST_PATH
        if test_file.is_symlink() or not test_file.is_file():
            raise DraftPublicationError("Verifier's actual test file missing")
        verifier_bytes = test_file.read_bytes()
        verifier_sha = validate_adversarial_test(verifier_bytes.decode("utf-8"))
        if verifier_sha != admission.get("verifier_test_sha256") or verifier_sha != verdict.get("verifier_test_sha256"):
            raise DraftPublicationError("Verifier test SHA mismatch")

        result_csv = p4_dir / "revenue_by_region.csv"
        if result_csv.is_symlink() or not result_csv.is_file():
            raise DraftPublicationError("Tested financial result CSV missing")
        csv_bytes = result_csv.read_bytes()
        if not csv_bytes or len(csv_bytes) > 50_000 or positive.get("output_sha256") != _sha(csv_bytes):
            raise DraftPublicationError("Published CSV is not identical to P4-tested CSV")
        oracle = compare_output(original / "sales.csv", result_csv)
        if oracle["output_sha256"] != _sha(csv_bytes) or oracle["net_revenue"] != positive.get("net_revenue"):
            raise DraftPublicationError("Independent financial reconciliation differs")

        if destination.exists():
            raise DraftPublicationError("Publisher staging destination already exists")
        destination.mkdir(parents=True)
        manifest_files: dict[str, str] = {}
        for entry in staged["files"]:
            path = entry["path"]
            if not is_candidate_path(path) or path == TEST_PATH:
                raise DraftPublicationError("Unauthorized candidate path for draft PR")
            body = (source_dir / path).read_bytes()
            if _sha(body) != entry["sha256"]:
                raise DraftPublicationError("Candidate file bytes differ from Engineer gate")
            dest = destination / path
            dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(body)
            manifest_files[path] = _sha(body)
        for path, body in ((TEST_PATH, verifier_bytes), ("revenue_by_region.csv", csv_bytes)):
            dest = destination / path
            dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(body)
            manifest_files[path] = _sha(body)

    manifest = {
        "schema_version": 1, "status": "HUMAN_REVIEW_REQUIRED",
        "source_run_id": run_id, "base_commit_sha": base_sha,
        "selected_iteration": iteration, "p3_candidate_status": p3["status"],
        "p4_independent_verifier_status": verdict["status"],
        "verifier_mutation_sensitivity": verdict["falsification_sensitivity"],
        "candidate_manifest_sha256": candidate_sha,
        "verifier_test_sha256": verifier_sha,
        "source_csv_sha256": source_hashes["sales.csv"],
        "original_tests_sha256": source_hashes["test_virtual_column.py"],
        "approved_policy_sha256": source_hashes["contracts/data_policy.json"],
        "verified_net_revenue": oracle["net_revenue"],
        "published_files": dict(sorted(manifest_files.items())),
        "approval": "NO_AGENT_POLICY_APPROVAL_OR_AUTOMERGE",
        "candidate_ci_status": "NOT_YET_RUN",
    }
    receipt_path = destination / "reports" / "agentic_delivery_manifest.json"
    receipt_path.parent.mkdir(exist_ok=True)
    receipt_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    body = destination / "draft-pr-body.md"
    body.write_text(
        "## Autonomous Data Engineering candidate - human review required\n\n"
        "Built from the original assignment, original employer tests and source CSV. "
        "The tested code was independently generated by three Foundry roles. "
        "Only deterministic gates can approve its objective tests.\n\n"
        f"- Source Actions run: https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/{run_id}\n"
        f"- Candidate iteration: {iteration} of at most three\n"
        "- P3 independent original tests, own tests, and finance oracle: PASSED\n"
        "- P4 independent Verifier-authored test: PASSED\n"
        "- P4 deliberate broken-function mutation detected: YES\n"
        f"- Independently checked regional net revenue: {oracle['net_revenue']}\n"
        f"- Source base commit SHA: {base_sha}\n"
        f"- Candidate file manifest SHA: {candidate_sha}\n\n"
        "DRAFT PR ONLY. No agent approved business policy or performed a merge. "
        "Independent branch CI must still run against the exact new commit SHA. "
        "Review all model-generated source and tests before any human merge.\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="P6 no-Azure draft-PR staging")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--base-sha", required=True)
    args = parser.parse_args()
    result = prepare_publication(
        artifacts=args.artifacts, original=args.original, destination=args.destination,
        run_id=args.run_id, base_sha=args.base_sha,
    )
    print(json.dumps({
        "status": result["status"], "iteration": result["selected_iteration"],
        "files": len(result["published_files"]), "candidate_ci": "PENDING",
    }))


if __name__ == "__main__":
    main()
