"""Isolated candidate workspace for a REAL Data Engineer, never a code runner.

In rebuild mode only the original CSV, employer tests and APPROVED policy
are mounted. In improve mode only allowlisted existing source files are copied.
LLM-generated code is written atomically and NEVER executed in the Foundry job.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .patch_policy import (
    CandidatePolicyError, MAX_CANDIDATE_FILES, MAX_TOTAL_BYTES,
    is_candidate_path, validate_candidate_content, validate_candidate_path,
)

PROTECTED = ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json")
Mode = Literal["rebuild", "improve"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe(root: Path, relative: str) -> Path:
    """Reject symlinks at any path component, including the output itself."""
    current = root
    for component in relative.split("/"):
        if component in ("", ".", ".."):
            raise CandidatePolicyError("Invalid relative component")
        current = current / component
        if current.is_symlink():
            raise CandidatePolicyError("Symlink path in candidate workspace")
    if not current.resolve().is_relative_to(root.resolve()):
        raise CandidatePolicyError("Candidate path escapes workspace")
    return current


@dataclass
class CandidateWorkspace:
    root: Path
    mode: Mode
    protected_hashes: dict[str, str]
    baseline: dict[str, bytes] = field(default_factory=dict)
    writes: list[dict[str, str]] = field(default_factory=list)
    validation_requests: list[dict] = field(default_factory=list)

    def verify_protected(self) -> None:
        for name, expected in self.protected_hashes.items():
            path = _safe(self.root, name)
            if not path.is_file() or _sha(path.read_bytes()) != expected:
                raise CandidatePolicyError("Original fixture or approved policy modified: " + name)

    def list_files(self) -> list[str]:
        self.verify_protected()
        result = []
        for path in self.root.rglob("*"):
            if path.is_symlink():
                raise CandidatePolicyError("Unknown symlink in candidate workspace")
            if path.is_file():
                name = path.relative_to(self.root).as_posix()
                if name not in PROTECTED and not is_candidate_path(name):
                    raise CandidatePolicyError("Unexpected candidate file")
                result.append(name)
        return sorted(result)

    def read_file(self, relative: str, offset: int = 0, limit: int = 14000) -> dict:
        if relative not in PROTECTED and not is_candidate_path(relative):
            raise CandidatePolicyError("Workspace read denied")
        if not isinstance(offset, int) or offset < 0 or offset > 2_000_000:
            raise CandidatePolicyError("Invalid read offset")
        if not isinstance(limit, int) or not 1 <= limit <= 16_000:
            raise CandidatePolicyError("Invalid read size")
        path = _safe(self.root, relative)
        if not path.is_file() or path.stat().st_size > 120_000:
            raise CandidatePolicyError("Workspace file missing or unexpectedly large")
        content = path.read_text(encoding="utf-8")
        return {
            "path": relative, "sha256": _sha(path.read_bytes()),
            "content": content[offset:offset + limit],
            "truncated": offset + limit < len(content),
            "total_characters": len(content),
        }

    def write_file(self, relative: str, content: str) -> dict[str, str]:
        name = validate_candidate_path(relative)
        payload = validate_candidate_content(name, content)
        self.verify_protected()
        current = [name for name in self.list_files() if is_candidate_path(name)]
        path = _safe(self.root, relative)
        if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
            raise CandidatePolicyError("Linked or invalid candidate output")
        if name not in current and len(current) >= MAX_CANDIDATE_FILES:
            raise CandidatePolicyError("Too many candidate files")
        size = sum(_safe(self.root, item).stat().st_size for item in current)
        old_size = path.stat().st_size if path.is_file() else 0
        if size - old_size + len(payload) > MAX_TOTAL_BYTES:
            raise CandidatePolicyError("Aggregate candidate limit exceeded")
        parent = path.parent
        if not parent.exists():
            if name.startswith("tests/") and parent == self.root / "tests":
                parent.mkdir(mode=0o700)
            else:
                raise CandidatePolicyError("Unexpected output directory")
        if parent.is_symlink() or not parent.is_dir():
            raise CandidatePolicyError("Linked output parent")
        fd, temporary = tempfile.mkstemp(prefix=".candidate-", dir=parent)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        receipt = {"path": name, "sha256": _sha(payload), "bytes": str(len(payload))}
        self.writes.append(receipt)
        self.verify_protected()
        return receipt

    def show_diff(self, relative: str) -> str:
        name = validate_candidate_path(relative)
        path = _safe(self.root, name)
        if not path.is_file():
            raise CandidatePolicyError("No candidate file to diff")
        previous = self.baseline.get(name, b"").decode("utf-8").splitlines(keepends=True)
        current = path.read_text(encoding="utf-8").splitlines(keepends=True)
        return "".join(difflib.unified_diff(
            previous, current, fromfile="base/" + name, tofile="candidate/" + name,
        ))[:18000]

    def request_validation(self, reason: str) -> dict:
        """Only WRITE a proposed validation receipt; sandbox P3 runs later."""
        if not isinstance(reason, str) or not 15 <= len(reason) <= 350:
            raise CandidatePolicyError("Missing meaningful validation reason")
        self.verify_protected()
        edited = [
            name for name in self.list_files()
            if is_candidate_path(name) and _sha(_safe(self.root, name).read_bytes())
            != (_sha(self.baseline[name]) if name in self.baseline else None)
        ]
        if self.mode == "rebuild" and not {"solution.py", "pipeline.py", "README.md"}.issubset(edited):
            raise CandidatePolicyError("Rebuild requires all original deliverables")
        if not edited:
            raise CandidatePolicyError("No real candidate changes")
        receipt = {
            "status": "PENDING_SANDBOX_VALIDATION", "mode": self.mode, "reason": reason,
            "files": [
                {"path": name, "sha256": _sha(_safe(self.root, name).read_bytes())}
                for name in edited
            ],
            "protected_hashes": dict(self.protected_hashes),
        }
        self.validation_requests.append(receipt)
        return receipt


def create_workspace(source: Path, destination: Path, mode: Mode) -> CandidateWorkspace:
    if mode not in ("rebuild", "improve"):
        raise CandidatePolicyError("Unsupported candidate mode")
    root = source.resolve(strict=True)
    if destination.exists() or destination.is_symlink():
        raise CandidatePolicyError("Candidate workspace must not exist")
    dest = destination.resolve()
    if dest == root or dest.is_relative_to(root):
        raise CandidatePolicyError("Candidate workspace must be outside original checkout")
    for name in PROTECTED:
        path = _safe(root, name)
        if not path.is_file() or path.stat().st_nlink != 1:
            raise CandidatePolicyError("Original fixture missing or linked: " + name)
    dest.mkdir(parents=True, mode=0o700)
    hashes = {}
    for name in PROTECTED:
        target = dest / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(_safe(root, name), target)
        target.chmod(0o444)
        hashes[name] = _sha(target.read_bytes())
    baseline = {}
    if mode == "improve":
        candidates = [root / name for name in ("solution.py", "pipeline.py", "README.md")]
        tests = root / "tests"
        if tests.is_dir() and not tests.is_symlink():
            candidates.extend(tests.glob("test_*.py"))
        for file in candidates:
            if file.is_symlink():
                raise CandidatePolicyError("Linked baseline candidate")
            if not file.is_file():
                continue
            relative = file.relative_to(root).as_posix()
            if not is_candidate_path(relative):
                continue
            if file.stat().st_size > 48_000:
                raise CandidatePolicyError("Baseline file too large")
            content = file.read_bytes()
            target = dest / relative
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(content)
            baseline[relative] = content
    workspace = CandidateWorkspace(
        root=dest, mode=mode, protected_hashes=hashes, baseline=baseline,
    )
    workspace.list_files()
    return workspace
