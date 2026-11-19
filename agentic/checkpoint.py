"""Cryptographically bound P5 checkpoints backed by real accepted job artifacts.

A checkpoint is a portable evidence reference, NOT a model statement or an
unsafe Python pickle. Revalidation verifies the original source and reruns
the trusted P5 controller before admitting any previous work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .delivery_status import evaluate_delivery_rounds

REQUIRED_ORIGINALS = ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json")


class CheckpointError(ValueError):
    """A checkpoint lacks evidence, contains a modified input, or cannot be trusted."""


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(path: Path) -> dict:
    item = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(item, dict):
        raise CheckpointError("Checkpoint source must be a JSON object")
    return item


def _inventory(artifacts: Path) -> dict[str, str]:
    if not artifacts.is_dir() or artifacts.is_symlink():
        raise CheckpointError("Evidence directory missing or symlinked")
    items = {}
    for path in sorted(artifacts.rglob("*")):
        if path.is_symlink():
            raise CheckpointError("Symlinked evidence is forbidden")
        if not path.is_file():
            continue
        if len(items) >= 150 or path.stat().st_size > 4_000_000:
            raise CheckpointError("Unbounded checkpoint contents")
        name = path.relative_to(artifacts).as_posix()
        if ".." in Path(name).parts:
            raise CheckpointError("Evidence path traversal")
        items[name] = _digest(path.read_bytes())
    if not items:
        raise CheckpointError("No staged evidence")
    return items


def capture_checkpoint(artifacts: Path, original: Path, state_file: Path,
                       *, run_id: str, base_sha: str, max_rounds: int = 3) -> dict:
    if not (run_id.isdecimal() and 5 <= len(run_id) <= 30):
        raise CheckpointError("Invalid original run ID")
    if len(base_sha) != 40 or any(c not in "0123456789abcdef" for c in base_sha):
        raise CheckpointError("Invalid 40-character source commit SHA")
    state = _json(state_file)
    manifest = _json(artifacts / "p2-architect-receipt/input_manifest.json")
    approved = _json(artifacts / "p2-architect-receipt/architect_gate.json")
    for name, field in (
        ("sales.csv", "source_csv_sha256"),
        ("test_virtual_column.py", "original_tests_sha256"),
        ("contracts/data_policy.json", "approved_policy_sha256"),
    ):
        if _digest((original / name).read_bytes()) != manifest.get(field):
            raise CheckpointError("Original source changed: " + name)
    if (approved.get("status") != "APPROVED_FOR_ENGINEERING"
            or approved.get("failures")
            or approved.get("source_sha256") != manifest["source_csv_sha256"]):
        raise CheckpointError("Architect was not independently approved")
    if (manifest.get("run_id") != run_id or manifest.get("base_commit") != base_sha
            or state.get("github_run_id") != run_id
            or state.get("base_commit_sha") != base_sha):
        raise CheckpointError("Source run or base SHA changed")
    if max_rounds not in (1, 2, 3) or state.get("max_iterations") != max_rounds:
        raise CheckpointError("Retry budget differs from original checkpoint")
    with tempfile.TemporaryDirectory(prefix="cloudfide-checkpoint-") as scratch:
        measured = evaluate_delivery_rounds(artifacts, original, Path(scratch), max_rounds)
    for key in ("status", "accepted_for_verification_iteration", "iterations_used",
                "max_iterations", "history"):
        if measured[key] != state.get(key):
            raise CheckpointError("P5 state differs from actual candidate/sandbox receipts: " + key)
    inventory = _inventory(artifacts)
    result = {
        "schema_version": 1,
        "source": "independent_p5_revalidation",
        "source_run_id": run_id,
        "base_commit_sha": base_sha,
        "status": state["status"],
        "selected_iteration": state["accepted_for_verification_iteration"],
        "max_iterations": max_rounds,
        "source_sha256": manifest["source_csv_sha256"],
        "original_tests_sha256": manifest["original_tests_sha256"],
        "approved_policy_sha256": manifest["approved_policy_sha256"],
        "state_sha256": _digest(state_file.read_bytes()),
        "artifact_sha256": inventory,
        "recovery_method": "github_actions_rerun_failed_jobs_or_exact_sha_candidate_ci",
        "auto_resume": False,
    }
    return result


def verify_checkpoint(checkpoint: dict, artifacts: Path, original: Path, state_file: Path) -> None:
    if checkpoint.get("schema_version") != 1 or checkpoint.get("source") != "independent_p5_revalidation":
        raise CheckpointError("Unknown checkpoint schema")
    rebuilt = capture_checkpoint(
        artifacts, original, state_file,
        run_id=checkpoint["source_run_id"],
        base_sha=checkpoint["base_commit_sha"],
        max_rounds=checkpoint["max_iterations"],
    )
    if rebuilt != checkpoint:
        raise CheckpointError("Checkpoint SHA inventory or stage state was changed")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-rounds", type=int, default=3, choices=(1, 2, 3))
    args = p.parse_args()
    state = _json(args.state)
    checkpoint = capture_checkpoint(
        args.artifacts, args.original, args.state,
        run_id=os.environ.get("GITHUB_RUN_ID") or state.get("github_run_id", ""),
        base_sha=os.environ.get("GITHUB_SHA") or state.get("base_commit_sha", ""),
        max_rounds=args.max_rounds,
    )
    verify_checkpoint(checkpoint, args.artifacts, args.original, args.state)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "checkpoint": "VERIFIED", "status": checkpoint["status"],
        "iteration": checkpoint["selected_iteration"],
        "artifact_count": len(checkpoint["artifact_sha256"]),
        "auto_resume": False,
    }))


if __name__ == "__main__":
    main()
