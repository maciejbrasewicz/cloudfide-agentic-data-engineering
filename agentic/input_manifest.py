"""Record source/policy/spec fingerprints for each candidate run.

Everything here is deterministic. The LLM does not get to assert that the input
is original or that it stayed unchanged: the orchestrator checks file bytes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from .schemas.requirements import InputManifest
from .spec_loader import TaskSpec


class InputIntegrityError(ValueError):
    """Required source evidence was replaced or is not a regular repository file."""


_FIXTURES = {
    "source_csv_sha256": "sales.csv",
    "original_tests_sha256": "test_virtual_column.py",
    "approved_policy_sha256": "contracts/data_policy.json",
}


def _sha256_file(root: Path, relative_path: str) -> str:
    """Reject symlinks, missing files and paths that escape the repository root."""
    file = root / relative_path
    if file.is_symlink() or not file.is_file():
        raise InputIntegrityError(f"Missing or redirected required input: {relative_path}")
    if not file.resolve().is_relative_to(root.resolve()):
        raise InputIntegrityError(f"Required input escapes the repository: {relative_path}")
    return hashlib.sha256(file.read_bytes()).hexdigest()


def create_input_manifest(
    *, root: Path, spec: TaskSpec, mode: Literal["rebuild", "improve"],
    base_commit: str, model_deployment: str, run_id: str | None = None,
) -> InputManifest:
    """Build a strictly typed, leak-free manifest from observed file bytes."""
    if not root.is_dir():
        raise InputIntegrityError("Repository root is missing")
    digests = {key: _sha256_file(root, path) for key, path in _FIXTURES.items()}
    return InputManifest(
        mode=mode,
        specification_sha256=spec.sha256,
        base_commit=base_commit,
        model_deployment=model_deployment,
        run_id=run_id,
        **digests,
    )


def verify_unchanged_inputs(root: Path, manifest: InputManifest) -> None:
    """Run before *and* after untrusted candidate evaluation."""
    for key, path in _FIXTURES.items():
        actual = _sha256_file(root, path)
        if actual != getattr(manifest, key):
            raise InputIntegrityError(f"Original input or approved policy changed: {path}")
