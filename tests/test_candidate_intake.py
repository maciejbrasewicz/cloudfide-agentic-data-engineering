"""P3 admission: no candidate bytes run before trusted SHA and path validation."""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from agentic.candidate_intake import CandidateIntakeError, verify_and_stage_candidate


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def setup_case(tmp_path: Path):
    root = tmp_path / "source"
    (root / "contracts").mkdir(parents=True)
    for name, content in [
        ("sales.csv", b"order,qty\n1,2\n"),
        ("test_virtual_column.py", b"def test_base(): assert True\n"),
        ("contracts/data_policy.json", b'{"version":1}\n'),
    ]:
        (root / name).write_bytes(content)
    candidate = b"def example():\n    return 42\n"
    archive = tmp_path / "candidate.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("solution.py", candidate)
    files = [{"path": "solution.py", "sha256": sha(candidate)}]
    gate = {
        "status": "CANDIDATE_READY_FOR_SANDBOX",
        "failures": [],
        "actual_written_files": files,
    }
    request = {
        "status": "PENDING_SANDBOX_VALIDATION",
        "files": files,
        "protected_hashes": {
            name: sha((root / name).read_bytes())
            for name in ("sales.csv", "test_virtual_column.py", "contracts/data_policy.json")
        },
    }
    return root, archive, gate, request


def intake(tmp_path: Path, root, archive, gate, request):
    return verify_and_stage_candidate(
        original_checkout=root, archive_path=archive, engineer_gate=gate,
        validation_request=request, destination=tmp_path / "staged",
    )


def test_valid_provenance_only_stages_bytes(tmp_path: Path):
    root, archive, gate, request = setup_case(tmp_path)
    receipt = intake(tmp_path, root, archive, gate, request)
    assert receipt["status"] == "VERIFIED_FOR_SECRET_FREE_SANDBOX"
    assert receipt["candidate_count"] == 1
    assert (tmp_path / "staged/solution.py").read_bytes() == b"def example():\n    return 42\n"
    assert (tmp_path / "staged/sales.csv").read_bytes() == (root / "sales.csv").read_bytes()


def test_claimed_hash_mismatch_fails_before_staging(tmp_path: Path):
    root, archive, gate, request = setup_case(tmp_path)
    gate["actual_written_files"][0]["sha256"] = "0" * 64
    with pytest.raises(CandidateIntakeError, match="disagree"):
        intake(tmp_path, root, archive, gate, request)
    assert not (tmp_path / "staged").exists()


@pytest.mark.parametrize("path", [
    "../secrets.txt", "/etc/passwd", "agentic/run.py", ".github/workflows/ci.yml",
    "tests/../test_foo.py", "tests/test_good.py/../../bad.py",
])
def test_forbidden_zip_entries_are_rejected(tmp_path: Path, path: str):
    root, archive, gate, request = setup_case(tmp_path)
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr(path, b"tamper")
    with pytest.raises(CandidateIntakeError):
        intake(tmp_path, root, archive, gate, request)
    assert not (tmp_path / "staged").exists()


def test_unapproved_agent_gate_cannot_be_forged(tmp_path: Path):
    root, archive, gate, request = setup_case(tmp_path)
    gate["status"] = "INCOMPLETE"
    with pytest.raises(CandidateIntakeError, match="did not pass"):
        intake(tmp_path, root, archive, gate, request)


def test_original_source_tampering_is_caught(tmp_path: Path):
    root, archive, gate, request = setup_case(tmp_path)
    (root / "sales.csv").write_text("tampered", encoding="utf-8")
    with pytest.raises(CandidateIntakeError, match="Original source hash"):
        intake(tmp_path, root, archive, gate, request)
    assert not (tmp_path / "staged").exists()


def test_request_must_be_pending_not_approved_by_agent(tmp_path: Path):
    root, archive, gate, request = setup_case(tmp_path)
    request["status"] = "VALIDATED"
    with pytest.raises(CandidateIntakeError, match="pending"):
        intake(tmp_path, root, archive, gate, request)


def test_substituted_zip_data_with_same_manifest_does_not_pass(tmp_path: Path):
    root, archive, gate, request = setup_case(tmp_path)
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("solution.py", "def evil():\n    return False\n")
    with pytest.raises(CandidateIntakeError, match="SHA-256"):
        intake(tmp_path, root, archive, gate, request)


def test_duplicate_zip_entry_denied(tmp_path: Path):
    root, archive, gate, request = setup_case(tmp_path)
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("solution.py", b"forged")
    with pytest.raises(CandidateIntakeError):
        intake(tmp_path, root, archive, gate, request)


def test_output_destination_must_be_new_and_outside_original(tmp_path: Path):
    root, archive, gate, request = setup_case(tmp_path)
    with pytest.raises(CandidateIntakeError, match="outside checkout"):
        verify_and_stage_candidate(
            original_checkout=root, archive_path=archive, engineer_gate=gate,
            validation_request=request, destination=root / "candidate",
        )
