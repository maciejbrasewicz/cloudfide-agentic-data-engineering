"""The recruiter replay must never execute model-authored Python outside Docker."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import replay_delivery as replay


SHA = "a" * 40
BASE = "b" * 40


@pytest.mark.parametrize("run_id", ["../../etc", "fake", "1", "2" * 40])
def test_replay_rejects_untrusted_run_before_any_git_call(monkeypatch, tmp_path: Path, run_id: str):
    monkeypatch.setattr(replay, "execute", lambda *_args, **_kwargs: pytest.fail("unsafe git"))
    with pytest.raises(ValueError, match="exact"):
        replay.prepare_branch(run_id, SHA, BASE, tmp_path)


def test_replay_fetches_one_exact_branch_then_uses_provenance_gate(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr(replay, "execute", lambda command, **kwargs: calls.append(command))
    def checked_stage(**kwargs):
        assert kwargs["branch"] == "agentic-delivery/run-44485096373"
        assert kwargs["commit_sha"] == SHA
        assert kwargs["base_sha"] == BASE
        assert kwargs["source_run_id"] == "44485096373"
        assert kwargs["destination"] == tmp_path
        return {"status": "ADMITTED_FOR_CANDIDATE_CI", "file_count": 6}
    monkeypatch.setattr(replay, "stage_exact_branch", checked_stage)
    result = replay.prepare_branch("44485096373", SHA, BASE, tmp_path)
    assert result["file_count"] == 6
    assert len(calls) == 1
    assert calls[0][:4] == ["git", "fetch", "--no-tags", "origin"]
    assert calls[0][-1] == (
        "refs/heads/agentic-delivery/run-44485096373:"
        "refs/remotes/origin/agentic-delivery/run-44485096373"
    )


def test_replay_must_have_docker_and_is_never_host_executed(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(replay.shutil, "which", lambda _name: None)
    monkeypatch.setattr(replay, "execute", lambda *_args, **_kwargs: pytest.fail("untrusted Python"))
    with pytest.raises(RuntimeError, match="Docker"):
        replay.verify_candidate(tmp_path / "candidate", tmp_path / "logs")


def test_replay_docker_flags_and_independent_oracle_enforced(monkeypatch, tmp_path: Path):
    from agentic import p3_oracle

    commands = []
    monkeypatch.setattr(replay.shutil, "which", lambda _name: "/usr/bin/docker")
    monkeypatch.setattr(replay, "execute", lambda command, **kwargs: commands.append(command))
    monkeypatch.setattr(p3_oracle, "validate_runner", lambda *_args: {
        "status": "PASSED", "reconciliation": "passed", "net_revenue": "2570247.03",
        "regions": {"Central": "515824.67"}, "source": "independent_p3_stdlib_oracle",
    })
    target = tmp_path / "logs"
    result = replay.verify_candidate(tmp_path / "candidate", target)
    assert result["status"] == "PASSED"
    assert len(commands) == 2
    container = commands[-1]
    for required in ("--network", "none", "--read-only", "--cap-drop", "ALL", "--user",
                     "65534:65534", "--memory", "768m"):
        assert required in container
    assert all(command[0] == "docker" for command in commands)
    assert json.loads((target / "verification.json").read_text())["reconciliation"] == "passed"


def test_replay_rejects_failed_independent_oracle(monkeypatch, tmp_path: Path):
    from agentic import p3_oracle
    monkeypatch.setattr(replay.shutil, "which", lambda _name: "/usr/bin/docker")
    monkeypatch.setattr(replay, "execute", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(p3_oracle, "validate_runner", lambda *_args: {
        "status": "FAILED", "failure": "original source controls do not match"
    })
    with pytest.raises(RuntimeError, match="Independent candidate validation failed"):
        replay.verify_candidate(tmp_path / "candidate", tmp_path / "logs")
