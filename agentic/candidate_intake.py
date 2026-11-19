"""P3: reject untrusted candidate archives before ANY code execution.

Validates exact trusted P2 file hashes, protected input bytes, file names,
regular ZIP entries and resource bounds. This module NEVER imports or runs the
generated Python; only the later no-network, no-secret container may do so.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path

from .patch_policy import (
    MAX_CANDIDATE_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES, is_candidate_path,
)
from .workspace import PROTECTED


class CandidateIntakeError(ValueError):
    """Candidate source or provenance is not safe for sandbox admission."""


_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _claims(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_CANDIDATE_FILES:
        raise CandidateIntakeError("Invalid " + label + " file count")
    claimed: dict[str, str] = {}
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise CandidateIntakeError("Malformed " + label + " file claim")
        name, checksum = entry["path"], entry["sha256"]
        if not is_candidate_path(name) or not isinstance(checksum, str) or not _HASH.fullmatch(checksum):
            raise CandidateIntakeError("Forbidden " + label + " path or checksum")
        if name.casefold() in {key.casefold() for key in claimed}:
            raise CandidateIntakeError("Duplicate case-insensitive candidate path")
        claimed[name] = checksum
    return claimed


def verify_and_stage_candidate(
    *, archive_path: Path, engineer_gate: dict, validation_request: dict,
    original_checkout: Path, destination: Path,
) -> dict:
    """Stage only P2-authorized bytes alongside fresh original inputs."""
    if engineer_gate.get("status") != "CANDIDATE_READY_FOR_SANDBOX" or engineer_gate.get("failures"):
        raise CandidateIntakeError("Engineer gate did not pass")
    if validation_request.get("status") != "PENDING_SANDBOX_VALIDATION":
        raise CandidateIntakeError("No pending isolated validation request")
    claims = _claims(engineer_gate.get("actual_written_files"), "gate")
    requests = _claims(validation_request.get("files"), "request")
    if claims != requests:
        raise CandidateIntakeError("Engineer gate and request SHA hashes disagree")
    expected = validation_request.get("protected_hashes")
    if not isinstance(expected, dict) or set(expected) != set(PROTECTED):
        raise CandidateIntakeError("Missing protected source fingerprint evidence")
    trusted_root = original_checkout.resolve(strict=True)
    for name in PROTECTED:
        source = trusted_root / name
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(trusted_root):
            raise CandidateIntakeError("Protected original input path is invalid")
        if not isinstance(expected[name], str) or not _HASH.fullmatch(expected[name]):
            raise CandidateIntakeError("Invalid original source hash format")
        if _sha(source.read_bytes()) != expected[name]:
            raise CandidateIntakeError("Original source hash differs from P2 receipt")
    if destination.exists() or destination.is_symlink():
        raise CandidateIntakeError("Destination must be new and empty")
    if destination.resolve().is_relative_to(trusted_root):
        raise CandidateIntakeError("Candidate extraction must stay outside checkout")
    accepted: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            entries = archive.infolist()
            if len(entries) != len(claims):
                raise CandidateIntakeError("ZIP entry count differs from verified P2 manifest")
            total_bytes = 0
            for entry in entries:
                name = entry.filename
                if not is_candidate_path(name) or name not in claims or name in accepted:
                    raise CandidateIntakeError("Unexpected or duplicate ZIP entry")
                if entry.flag_bits & 0x1 or entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16):
                    raise CandidateIntakeError("Encrypted, linked, or directory entry denied")
                if entry.file_size > MAX_FILE_BYTES:
                    raise CandidateIntakeError("Candidate file exceeds size cap")
                total_bytes += entry.file_size
                if total_bytes > MAX_TOTAL_BYTES:
                    raise CandidateIntakeError("Candidate archive exceeds total size cap")
                contents = archive.read(entry)
                if len(contents) != entry.file_size or _sha(contents) != claims[name]:
                    raise CandidateIntakeError("Candidate ZIP bytes fail SHA-256 admission")
                accepted[name] = contents
    except (zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise CandidateIntakeError("Candidate ZIP is corrupted") from exc
    if set(accepted) != set(claims):
        raise CandidateIntakeError("Candidate ZIP omitted a required file")
    destination.mkdir(parents=True)
    for name in PROTECTED:
        source = trusted_root / name
        target = destination / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o444)
    for name, data in accepted.items():
        target = destination / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(data)
    return {
        "status": "VERIFIED_FOR_SECRET_FREE_SANDBOX",
        "candidate_count": len(accepted),
        "files": [{"path": path, "sha256": _sha(data)}
                  for path, data in sorted(accepted.items())],
        "protected_hashes": expected,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify_and_stage_candidate(
        archive_path=args.archive,
        engineer_gate=json.loads(args.gate.read_text(encoding="utf-8")),
        validation_request=json.loads(args.request.read_text(encoding="utf-8")),
        original_checkout=args.original,
        destination=args.destination,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "candidate_count": receipt["candidate_count"]}))


if __name__ == "__main__":
    main()
