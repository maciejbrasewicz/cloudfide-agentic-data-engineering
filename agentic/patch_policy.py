"""Strict write allowlist for untrusted Data Engineer candidate changes.

This module validates *bytes and paths only*. Candidate Python is NEVER executed
in the Foundry job; a separate secret-free P3 runner will do that.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


class CandidatePolicyError(ValueError):
    """An agent attempted an edit outside the approved candidate boundary."""


_TEST_FILE = re.compile(r"tests/test_[A-Za-z0-9_]+\.py\Z")
MAX_FILE_BYTES = 48_000
MAX_CANDIDATE_FILES = 30
MAX_TOTAL_BYTES = 500_000


def is_candidate_path(relative: str) -> bool:
    return isinstance(relative, str) and (
        relative in {"solution.py", "pipeline.py", "README.md"}
        or bool(_TEST_FILE.fullmatch(relative))
    )


def validate_candidate_path(relative: str) -> str:
    if not is_candidate_path(relative):
        raise CandidatePolicyError("Candidate path is not on the write allowlist")
    if "\\" in relative or Path(relative).as_posix() != relative:
        raise CandidatePolicyError("Invalid candidate path separator")
    return relative


def validate_candidate_content(relative: str, content: str) -> bytes:
    validate_candidate_path(relative)
    if not isinstance(content, str) or "\x00" in content or "\r" in content:
        raise CandidatePolicyError("Only normalized UTF-8 source text is accepted")
    payload = content.encode("utf-8")
    if not payload or len(payload) > MAX_FILE_BYTES:
        raise CandidatePolicyError("Candidate content outside the file size limit")
    if relative.endswith(".py"):
        try:
            ast.parse(content, filename=relative)
        except (SyntaxError, ValueError) as exc:
            raise CandidatePolicyError("Candidate Python has invalid syntax") from exc
    return payload
