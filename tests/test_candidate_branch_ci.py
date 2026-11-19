"""P6 branch CI must prove actual Git commit SHA and allowed, SHA-matched diff."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from agentic.candidate_branch_ci import CandidateCIError, stage_exact_branch
from agentic.verifier_gate import TEST_PATH, validate_adversarial_test


RUN = "12345"
BRANCH = "agentic-delivery/run-12345"
TEST = (
    "import pandas as pd\nfrom solution import add_virtual_column\n\n"
    "def test_real_math():\n"
    "    x = pd.DataFrame({'a': [2], 'b': [3]})\n"
    "    assert add_virtual_column(x, 'a + b', 'total').at[0, 'total'] == 5\n"
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> str:
    output = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True,
        timeout=10, text=True,
    )
    return output.stdout.strip()


def stage_repo(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "CI fixture")
    git(root, "config", "user.email", "fixture@example.test")
    git(root, "config", "core.autocrlf", "false")
    original = {
        "sales.csv": b"original,value\n1,2\n",
        "test_virtual_column.py": b"def test_base(): assert True\n",
        "contracts/data_policy.json": b'{"version":1}\n',
    }
    for name, content in original.items():
        path = root / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(content)
    git(root, "add", ".")
    git(root, "commit", "-m", "original trusted base")
    base = git(root, "rev-parse", "HEAD")
    delivery = root / "deliveries" / ("run-" + RUN)
    generated = {
        "solution.py": b"def add_virtual_column(df, role, name):\n    return df\n",
        "pipeline.py": b"def main():\n    return 1\n",
        "README.md": b"New candidate README. Human review pending.\n",
        "revenue_by_region.csv": b"region,revenue\nCentral,1.00\n",
        "tests/test_generated.py": b"def test_case():\n    assert True\n",
        TEST_PATH: TEST.encode(),
    }
    for name, content in generated.items():
        path = delivery / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(content)
    report = delivery / "reports/agentic_delivery_manifest.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps({
        "status": "HUMAN_REVIEW_REQUIRED",
        "approval": "NO_AGENT_POLICY_APPROVAL_OR_AUTOMERGE",
        "source_run_id": RUN, "base_commit_sha": base,
        "p3_candidate_status": "PASSED",
        "p4_independent_verifier_status": "PASSED",
        "verifier_mutation_sensitivity": "PASSED",
        "verifier_test_sha256": validate_adversarial_test(TEST),
        "candidate_manifest_sha256": "f" * 64,
        "source_csv_sha256": sha(original["sales.csv"]),
        "original_tests_sha256": sha(original["test_virtual_column.py"]),
        "approved_policy_sha256": sha(original["contracts/data_policy.json"]),
        "published_files": {name: sha(contents) for name, contents in generated.items()},
    }), encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "published candidate")
    head = git(root, "rev-parse", "HEAD")
    git(root, "update-ref", "refs/remotes/origin/" + BRANCH, head)
    return root, base, head


def verify(root: Path, base: str, head: str, output: Path):
    return stage_exact_branch(
        root=root, destination=output, branch=BRANCH,
        commit_sha=head, base_sha=base, source_run_id=RUN,
    )


def test_exact_sha_candidate_stages_only_approved_data(tmp_path: Path):
    root, base, head = stage_repo(tmp_path)
    result = verify(root, base, head, tmp_path / "stage")
    assert result["status"] == "ADMITTED_FOR_CANDIDATE_CI"
    assert result["candidate_sha"] == head
    assert (tmp_path / "stage" / TEST_PATH).read_text() == TEST
    assert (tmp_path / "stage/sales.csv").read_bytes() == (root / "sales.csv").read_bytes()
    assert len(result["candidate_manifest_sha256"]) == 64


def test_moved_branch_rejected_even_if_candidate_sha_was_valid(tmp_path: Path):
    root, base, head = stage_repo(tmp_path)
    git(root, "commit", "--allow-empty", "-m", "branch moved")
    git(root, "update-ref", "refs/remotes/origin/" + BRANCH, git(root, "rev-parse", "HEAD"))
    with pytest.raises(CandidateCIError, match="branch moved"):
        verify(root, base, head, tmp_path / "stage")


def test_untrusted_additional_path_outside_allowlist_fails(tmp_path: Path):
    root, base, _ = stage_repo(tmp_path)
    (root / "agentic").mkdir()
    (root / "agentic/agent_override.py").write_text("malicious = True\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "unauthorized new file")
    new = git(root, "rev-parse", "HEAD")
    git(root, "update-ref", "refs/remotes/origin/" + BRANCH, new)
    with pytest.raises(CandidateCIError):
        verify(root, base, new, tmp_path / "stage")


def test_forged_file_hash_is_detected(tmp_path: Path):
    root, base, _ = stage_repo(tmp_path)
    manifest = root / "deliveries" / ("run-" + RUN) / "reports/agentic_delivery_manifest.json"
    data = json.loads(manifest.read_text())
    data["published_files"]["solution.py"] = "0" * 64
    manifest.write_text(json.dumps(data), encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "--amend", "--no-edit")
    new = git(root, "rev-parse", "HEAD")
    git(root, "update-ref", "refs/remotes/origin/" + BRANCH, new)
    with pytest.raises(CandidateCIError, match="SHA-bound"):
        verify(root, base, new, tmp_path / "stage")


def test_source_run_id_mismatch_is_rejected(tmp_path: Path):
    root, base, head = stage_repo(tmp_path)
    with pytest.raises(CandidateCIError, match="run id"):
        stage_exact_branch(
            root=root, destination=tmp_path / "stage",
            branch=BRANCH, commit_sha=head, base_sha=base,
            source_run_id="99999",
        )
