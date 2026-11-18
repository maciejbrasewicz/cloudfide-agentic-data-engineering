"""Load the original CloudFide assignment only from an external runtime source.

The source document is explicitly excluded from this repository. This module never
persists or logs the specification text; only its SHA-256 may enter a run manifest.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


MAX_SPEC_BYTES = 65_536
_REQUIRED_MARKERS = (
    "add_virtual_column", "solution.py", "pipeline.py", "sales.csv",
    "test_virtual_column.py", "revenue_by_region.csv", "README.md",
)


class SpecInputError(ValueError):
    """The assignment input is missing, invalid, or on a forbidden path."""


@dataclass(frozen=True, repr=False)
class TaskSpec:
    """Runtime-only task text. Repr intentionally excludes confidential content."""

    text: str
    sha256: str
    source: Literal["runtime_file", "actions_secret"]

    def __repr__(self) -> str:
        return f"TaskSpec(sha256={self.sha256!r}, source={self.source!r}, text=<redacted>)"


def load_task_spec(*, repo_root: Path, path: Path | None = None, encoded: str | None = None) -> TaskSpec:
    """Load exactly one runtime source, rejecting specs placed inside the checkout.

    GitHub Actions should pass a BASE64-encoded GitHub Secret via *encoded*; local
    operators may use a file completely outside the Git checkout. Base64 is not
    encryption: confidentiality rests on the GitHub Secret and runner permissions.
    """
    if (path is None) == (encoded is None):
        raise SpecInputError("Provide exactly one specification source: external path or secret")
    if path is not None:
        root = repo_root.resolve(strict=True)
        if path.is_symlink():
            raise SpecInputError("Specification must be a regular external file, not a symlink")
        try:
            source_path = path.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise SpecInputError("Specification file does not exist or is inaccessible") from exc
        if source_path == root or source_path.is_relative_to(root):
            raise SpecInputError("Original task specification must stay outside the repository")
        if not source_path.is_file():
            raise SpecInputError("Specification source is not a regular file")
        if source_path.stat().st_size > MAX_SPEC_BYTES:
            raise SpecInputError("Specification exceeds the supported size limit")
        raw = source_path.read_bytes()
        source: Literal["runtime_file", "actions_secret"] = "runtime_file"
    else:
        try:
            raw = base64.b64decode(encoded or "", validate=True)
        except (binascii.Error, ValueError) as exc:
            raise SpecInputError("Invalid encoded specification") from exc
        source = "actions_secret"

    if not raw or len(raw) > MAX_SPEC_BYTES or b"\x00" in raw:
        raise SpecInputError("Empty, oversized, or invalid specification content")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SpecInputError("Specification must be valid UTF-8") from exc
    missing = [marker for marker in _REQUIRED_MARKERS if marker not in text]
    if missing:
        raise SpecInputError("Specification is missing required assignment references: " + ", ".join(missing))
    return TaskSpec(text=text, sha256=hashlib.sha256(raw).hexdigest(), source=source)
