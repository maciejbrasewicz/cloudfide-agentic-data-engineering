"""Trusted no-secret CI intake of a GitHub PR branch at an EXACT expected SHA.

The candidate branch is never checked out as executable host code. Git show
reads only allowlisted file bytes from an SHA linked to the publisher manifest,
which are then executed inside the same no-network P3 Docker sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from .patch_policy import is_candidate_path
from .verifier_gate import TEST_PATH, validate_adversarial_test


class CandidateCIError(ValueError):
    """Draft branch changed or differs from the exact independently tested files."""


SHA = re.compile(r"^[0-9a-f]{40}$")
BRANCH = re.compile(r"^agentic-delivery/run-(\d{5,30})$")


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=root, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=15,
    )
    if result.returncode != 0:
        raise CandidateCIError("Git source verification failed: " + args[0])
    return result.stdout


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _published_path(name: str) -> bool:
    return is_candidate_path(name) or name == "revenue_by_region.csv"


def stage_exact_branch(
    *, root: Path, destination: Path, branch: str,
    commit_sha: str, base_sha: str, source_run_id: str,
) -> dict:
    match = BRANCH.fullmatch(branch)
    if not match or match.group(1) != source_run_id or not source_run_id.isdecimal():
        raise CandidateCIError("Candidate ref or run id outside trusted publication format")
    if not SHA.fullmatch(commit_sha) or not SHA.fullmatch(base_sha):
        raise CandidateCIError("Expected and base commit hashes must be full SHA-1")
    # The trusted GitHub CI job fetches the branch after checkout and then
    # passes its exact immutable commit into this function.
    ref_name = "refs/remotes/origin/" + branch
    actual_sha = _git(root, "rev-parse", ref_name).decode().strip()
    if actual_sha != commit_sha:
        raise CandidateCIError("Draft PR branch moved since CI dispatch")
    parent = _git(root, "rev-parse", commit_sha + "^").decode().strip()
    if parent != base_sha:
        raise CandidateCIError("Draft commit does not descend directly from approved base")
    diff_lines = _git(root, "diff", "--name-status", base_sha, commit_sha).decode().splitlines()
    modified: set[str] = set()
    for line in diff_lines:
        fields = line.split("\t")
        if len(fields) != 2 or fields[0] not in ("M", "A"):
            raise CandidateCIError("Unexpected removed/renamed or untrusted draft file")
        name = fields[1]
        if not _published_path(name) and name != "reports/agentic_delivery_manifest.json":
            raise CandidateCIError("Candidate draft changes non-allowlisted path: " + name)
        modified.add(name)
    if "reports/agentic_delivery_manifest.json" not in modified:
        raise CandidateCIError("Trusted publication manifest missing from candidate commit")

    data = _git(root, "show", commit_sha + ":reports/agentic_delivery_manifest.json")
    if len(data) > 100_000:
        raise CandidateCIError("Oversized publication manifest")
    manifest = json.loads(data.decode("utf-8"))
    if (
        manifest.get("status") != "HUMAN_REVIEW_REQUIRED"
        or manifest.get("approval") != "NO_AGENT_POLICY_APPROVAL_OR_AUTOMERGE"
        or manifest.get("source_run_id") != source_run_id
        or manifest.get("base_commit_sha") != base_sha
        or manifest.get("p3_candidate_status") != "PASSED"
        or manifest.get("p4_independent_verifier_status") != "PASSED"
        or manifest.get("verifier_mutation_sensitivity") != "PASSED"
    ):
        raise CandidateCIError("Draft publication evidence is not approved for review")
    claims = manifest.get("published_files")
    if not isinstance(claims, dict) or not 4 <= len(claims) <= 36:
        raise CandidateCIError("Missing or excessive candidate file claims")
    if not {"solution.py", "pipeline.py", "README.md",
            TEST_PATH, "revenue_by_region.csv"}.issubset(claims):
        raise CandidateCIError("Required candidate deliverables missing")
    if set(claims) != modified - {"reports/agentic_delivery_manifest.json"}:
        raise CandidateCIError("Draft actual diff and claimed candidate files differ")
    for protected, field in (
        ("sales.csv", "source_csv_sha256"),
        ("test_virtual_column.py", "original_tests_sha256"),
        ("contracts/data_policy.json", "approved_policy_sha256"),
    ):
        original_data = (root / protected).read_bytes()
        if _sha(original_data) != manifest.get(field):
            raise CandidateCIError("Original employer input differs from source-run approval")

    if destination.exists():
        raise CandidateCIError("Candidate CI staging destination must be new")
    destination.mkdir(parents=True)
    for name in ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json"):
        target = destination / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((root / name).read_bytes())
        target.chmod(0o444)
    for name, expected_sha in claims.items():
        if not _published_path(name) or not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise CandidateCIError("Unapproved path or malformed file hash")
        contents = _git(root, "show", commit_sha + ":" + name)
        if not contents or len(contents) > 60_000 or _sha(contents) != expected_sha:
            raise CandidateCIError("Published file bytes differ from SHA-bound source run")
        if name == TEST_PATH and validate_adversarial_test(contents.decode("utf-8")) != manifest["verifier_test_sha256"]:
            raise CandidateCIError("Verifier test file differs from accepted original")
        target = destination / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(contents)
    return {
        "status": "ADMITTED_FOR_CANDIDATE_CI",
        "source_run_id": source_run_id, "base_sha": base_sha,
        "candidate_sha": commit_sha, "file_count": len(claims),
        "candidate_manifest_sha256": manifest["candidate_manifest_sha256"],
        "original_fixtures_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="P6 exact-SHA isolated candidate branch CI")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    result = stage_exact_branch(
        root=args.root, destination=args.stage, branch=args.branch,
        commit_sha=args.sha, base_sha=args.base, source_run_id=args.source_run_id,
    )
    args.receipt.parent.mkdir(exist_ok=True, parents=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
