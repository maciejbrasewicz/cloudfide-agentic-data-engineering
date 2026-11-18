"""P2 workspace security: model writes cannot modify original task or escape allowlist."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from agentic.patch_policy import CandidatePolicyError, validate_candidate_path
from agentic.workspace import create_workspace


def fixture_project(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "contracts").mkdir(parents=True)
    (root / "sales.csv").write_text("order,quantity\n1,2\n", encoding="utf-8")
    (root / "test_virtual_column.py").write_text("def test_base(): assert True\n", encoding="utf-8")
    (root / "contracts/data_policy.json").write_text('{"version":1}\n', encoding="utf-8")
    (root / "solution.py").write_text("def old(): return 1\n", encoding="utf-8")
    return root


def test_rebuild_hides_existing_code_and_writes_real_candidate(tmp_path: Path):
    source = fixture_project(tmp_path)
    ws = create_workspace(source, tmp_path / "generated", "rebuild")
    assert ws.list_files() == ["contracts/data_policy.json", "sales.csv", "test_virtual_column.py"]
    with pytest.raises(CandidatePolicyError, match="missing"):
        ws.read_file("solution.py")
    ws.write_file("solution.py", "def add_virtual_column(x, y, z):\n    return x\n")
    ws.write_file("pipeline.py", "def main():\n    return 1\n")
    ws.write_file("README.md", "Implementation description and operating instructions.")
    ws.write_file("tests/test_generated.py", "def test_new():\n    assert True\n")
    receipt = ws.request_validation("Independent sandbox validation required before acceptance")
    assert receipt["status"] == "PENDING_SANDBOX_VALIDATION"
    assert len(receipt["files"]) == 4
    assert len(ws.writes) == 4
    assert (source / "solution.py").read_text() == "def old(): return 1\n"
    assert "solution.py" in ws.show_diff("solution.py")


def test_rebuild_incomplete_without_required_files(tmp_path: Path):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "rebuild")
    ws.write_file("solution.py", "def f():\n    return 1\n")
    with pytest.raises(CandidatePolicyError, match="requires"):
        ws.request_validation("Require independent sandbox evaluation of the complete code")


@pytest.mark.parametrize("invalid", [
    "sales.csv", "test_virtual_column.py", "contracts/data_policy.json",
    "../sales.csv", "tests/../../secrets.py", "agentic/architect.py",
    ".github/workflows/ci.yml", "uv.lock", ".env", "tests/conftest.py",
    "tests/private/test_x.py", "tests/test_bad.py/../x.py",
    "tests\\test_new.py", "tests/test_bad.py/other", "/tmp/test_bad.py",
    "tests/test-invalid.py", "tests/test_ą.py",
])
def test_rejects_forbidden_write_paths(tmp_path: Path, invalid: str):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "rebuild")
    with pytest.raises(CandidatePolicyError):
        validate_candidate_path(invalid)
    with pytest.raises(CandidatePolicyError):
        ws.write_file(invalid, "def valid():\n    return 1\n")


def test_rejects_invalid_syntax_and_large_content(tmp_path: Path):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "rebuild")
    with pytest.raises(CandidatePolicyError, match="syntax"):
        ws.write_file("solution.py", "def broken(:\n")
    with pytest.raises(CandidatePolicyError, match="size"):
        ws.write_file("README.md", "x" * 50000)
    with pytest.raises(CandidatePolicyError):
        ws.write_file("solution.py", "x\x00y")


def test_tampered_original_csv_fails_all_gates(tmp_path: Path):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "rebuild")
    protected = ws.root / "sales.csv"
    protected.chmod(0o600)
    protected.write_text("evil", encoding="utf-8")
    with pytest.raises(CandidatePolicyError, match="modified"):
        ws.list_files()
    with pytest.raises(CandidatePolicyError, match="modified"):
        ws.write_file("solution.py", "def f():\n    return 1\n")


def test_symlink_to_secret_cannot_be_overwritten(tmp_path: Path):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "rebuild")
    secret = tmp_path / "credentials.py"
    secret.write_text("secret", encoding="utf-8")
    try:
        (ws.root / "solution.py").symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not available on this runner")
    with pytest.raises(CandidatePolicyError, match="Symlink"):
        ws.write_file("solution.py", "def f():\n    return 1\n")
    assert secret.read_text() == "secret"


def test_symlink_parent_cannot_redirect_test_write(tmp_path: Path):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "rebuild")
    try:
        (ws.root / "tests").symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not available on this runner")
    with pytest.raises(CandidatePolicyError, match="Symlink"):
        ws.write_file("tests/test_redirect.py", "def test_yes():\n    assert True\n")


def test_hardlink_to_source_cannot_be_overwritten(tmp_path: Path):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "rebuild")
    try:
        os.link(ws.root / "sales.csv", ws.root / "solution.py")
    except OSError:
        pytest.skip("Hardlinks not supported")
    with pytest.raises(CandidatePolicyError, match="Linked"):
        ws.write_file("solution.py", "def f():\n    return 1\n")


def test_improve_loads_only_allowlisted_baseline(tmp_path: Path):
    root = fixture_project(tmp_path)
    (root / ".env").write_text("SECRET=protected", encoding="utf-8")
    (root / "agentic").mkdir()
    (root / "agentic/run.py").write_text("restricted implementation", encoding="utf-8")
    ws = create_workspace(root, tmp_path / "generated", "improve")
    assert ws.read_file("solution.py")["content"] == "def old(): return 1\n"
    assert ".env" not in ws.list_files()
    assert "agentic/run.py" not in ws.list_files()
    assert ws.show_diff("solution.py") == ""
    ws.write_file("solution.py", "def old():\n    return 2\n")
    assert "+    return 2" in ws.show_diff("solution.py")


def test_improve_cannot_validate_without_changes(tmp_path: Path):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "improve")
    with pytest.raises(CandidatePolicyError, match="No real"):
        ws.request_validation("No changes should not allow a fake PASS receipt")


def test_workspace_cannot_be_inside_original_checkout(tmp_path: Path):
    original = fixture_project(tmp_path)
    with pytest.raises(CandidatePolicyError, match="outside"):
        create_workspace(original, original / "candidate", "rebuild")


def test_validation_request_never_runs_candidate_code(tmp_path: Path):
    ws = create_workspace(fixture_project(tmp_path), tmp_path / "generated", "rebuild")
    malicious = "import os\nos.system('exit 99')\n"
    ws.write_file("solution.py", malicious)
    ws.write_file("pipeline.py", "def main():\n    return 1\n")
    ws.write_file("README.md", "Actual candidate authoring has not been validated.")
    receipt = ws.request_validation("Request sandbox check, not any execution inside Azure")
    assert receipt["status"] == "PENDING_SANDBOX_VALIDATION"
    assert len(ws.validation_requests) == 1
