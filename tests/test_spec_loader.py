"""P0 input and provenance gates: no spec persistence, no fixture tampering."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentic.input_manifest import (
    InputIntegrityError, create_input_manifest, verify_unchanged_inputs,
)
from agentic.schemas.requirements import InputManifest
from agentic.spec_loader import SpecInputError, load_task_spec


TASK = (
    "CloudFide original task. add_virtual_column in solution.py. "
    "Read sales.csv; implement pipeline.py and revenue_by_region.csv. "
    "Keep test_virtual_column.py and write README.md. SPEC_CONTENT_SENTINEL."
)


def repo_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "contracts").mkdir(parents=True)
    (root / "sales.csv").write_text("order,quantity\n1,2\n", encoding="utf-8")
    (root / "test_virtual_column.py").write_text("def test_sample(): pass\n", encoding="utf-8")
    (root / "contracts/data_policy.json").write_text('{"version":1}\n', encoding="utf-8")
    return root


def test_external_spec_and_secret_have_same_digest(tmp_path: Path) -> None:
    root = repo_fixture(tmp_path)
    source = tmp_path / "private-task.md"
    source.write_text(TASK, encoding="utf-8")
    external = load_task_spec(repo_root=root, path=source)
    secret = load_task_spec(repo_root=root, encoded=base64.b64encode(TASK.encode()).decode())
    assert external.sha256 == secret.sha256
    assert external.source == "runtime_file"
    assert secret.source == "actions_secret"
    assert "SPEC_CONTENT_SENTINEL" not in repr(secret)



def test_plain_utf8_actions_secret_matches_base64_and_never_logs_content(tmp_path: Path) -> None:
    root = repo_fixture(tmp_path)
    plain = load_task_spec(repo_root=root, encoded=TASK + " → original task")
    b64 = load_task_spec(
        repo_root=root,
        encoded=base64.b64encode((TASK + " → original task").encode("utf-8")).decode("ascii"),
    )
    assert plain.sha256 == b64.sha256
    assert plain.text == b64.text
    assert plain.source == "actions_secret"
    assert "SPEC_CONTENT_SENTINEL" not in repr(plain)
    assert "→" not in repr(plain)


def test_random_non_base64_plaintext_is_not_a_valid_original_task(tmp_path: Path) -> None:
    root = repo_fixture(tmp_path)
    with pytest.raises(SpecInputError):
        load_task_spec(repo_root=root, encoded="private → but not the original assignment")



def test_missing_or_multiple_sources_are_rejected(tmp_path: Path) -> None:
    root = repo_fixture(tmp_path)
    with pytest.raises(SpecInputError):
        load_task_spec(repo_root=root)
    with pytest.raises(SpecInputError):
        load_task_spec(repo_root=root, path=tmp_path / "missing.md", encoded="AAAA")
    with pytest.raises(SpecInputError, match="does not exist"):
        load_task_spec(repo_root=root, path=tmp_path / "missing.md")
    with pytest.raises(SpecInputError):
        load_task_spec(repo_root=root, encoded="not valid base64")


def test_spec_inside_repo_is_rejected(tmp_path: Path) -> None:
    root = repo_fixture(tmp_path)
    source = root / "taskvirtualcolumn.md"
    source.write_text(TASK, encoding="utf-8")
    with pytest.raises(SpecInputError, match="outside the repository"):
        load_task_spec(repo_root=root, path=source)


def test_missing_required_spec_references_are_rejected(tmp_path: Path) -> None:
    root = repo_fixture(tmp_path)
    with pytest.raises(SpecInputError, match="missing required"):
        load_task_spec(repo_root=root, encoded=base64.b64encode(b"not a task").decode())


def test_manifest_records_hashes_without_leaking_spec(tmp_path: Path) -> None:
    root = repo_fixture(tmp_path)
    spec = load_task_spec(repo_root=root, encoded=base64.b64encode(TASK.encode()).decode())
    receipt = create_input_manifest(
        root=root, spec=spec, mode="rebuild", base_commit="1234567890abcdef1234567890abcdef12345678",
        model_deployment="gpt-5.6-sol", run_id="example-run",
    )
    doc = receipt.model_dump_json()
    assert "SPEC_CONTENT_SENTINEL" not in doc
    assert "add_virtual_column" not in doc
    assert spec.sha256 in doc
    assert receipt.schema_version == 1
    verify_unchanged_inputs(root, receipt)
    with pytest.raises(ValidationError):
        InputManifest.model_validate({**json.loads(doc), "secret": "should-fail"})


@pytest.mark.parametrize("changed", ["sales.csv", "test_virtual_column.py", "contracts/data_policy.json"])
def test_modified_fixture_or_policy_is_detected(tmp_path: Path, changed: str) -> None:
    root = repo_fixture(tmp_path)
    spec = load_task_spec(repo_root=root, encoded=base64.b64encode(TASK.encode()).decode())
    manifest = create_input_manifest(
        root=root, spec=spec, mode="improve", base_commit="1234567890abcdef1234567890abcdef12345678",
        model_deployment="gpt-5.6-sol",
    )
    (root / changed).write_text("tampered", encoding="utf-8")
    with pytest.raises(InputIntegrityError, match="changed"):
        verify_unchanged_inputs(root, manifest)


def test_symlinked_input_is_rejected(tmp_path: Path) -> None:
    root = repo_fixture(tmp_path)
    target = tmp_path / "outside.csv"
    target.write_text("different", encoding="utf-8")
    (root / "sales.csv").unlink()
    (root / "sales.csv").symlink_to(target)
    spec = load_task_spec(repo_root=root, encoded=base64.b64encode(TASK.encode()).decode())
    with pytest.raises(InputIntegrityError, match="redirected"):
        create_input_manifest(root=root, spec=spec, mode="rebuild", base_commit="1234567890abcdef1234567890abcdef12345678",model_deployment="gpt-5.6-sol")
