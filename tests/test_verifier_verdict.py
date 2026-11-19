"""P4 independent verdict requires both positive code execution and a negative control."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic.verifier_verdict import IndependentVerifierError, assess_verifier


def setup_case(tmp_path: Path):
    admission = tmp_path / "admission.json"
    admission.write_text(json.dumps({
        "status": "ADMITTED_FOR_INDEPENDENT_ADVERSARIAL_TEST",
        "iteration": 1,
        "candidate_manifest_sha256": "a" * 64,
        "verifier_test_sha256": "b" * 64,
        "verifier_model_next_action": "request_independent_test",
    }), encoding="utf-8")
    positive = tmp_path / "good"
    negative = tmp_path / "bad"
    positive.mkdir()
    negative.mkdir()
    (positive / "verification.json").write_text(json.dumps({
        "source": "independent_p3_stdlib_oracle", "status": "PASSED",
        "sandbox_test_exit_code": 0, "sandbox_pipeline_exit_code": 0,
    }), encoding="utf-8")
    for name in ("test_exit_code.txt", "pipeline_exit_code.txt"):
        (positive / name).write_text("0", encoding="utf-8")
    (negative / "test_exit_code.txt").write_text("1", encoding="utf-8")
    (positive / "tests.log").write_text("2 passed", encoding="utf-8")
    (negative / "tests.log").write_text("1 failed", encoding="utf-8")
    return admission, positive, negative


def test_real_mutation_detection_and_candidate_pass():
    import tempfile
    with tempfile.TemporaryDirectory() as root:
        admission, good, bad = setup_case(Path(root))
        result = assess_verifier(admission=admission, positive=good, negative=bad)
        assert result["status"] == "PASSED"
        assert result["falsification_sensitivity"] == "PASSED"
        assert result["next_stage"] == "P6_DRAFT_PR_REVIEW"


def test_useless_test_that_passes_broken_code_fails_verifier(tmp_path: Path):
    admission, good, bad = setup_case(tmp_path)
    (bad / "test_exit_code.txt").write_text("0", encoding="utf-8")
    result = assess_verifier(admission=admission, positive=good, negative=bad)
    assert result["status"] == "WEAK_VERIFIER_TEST"
    assert result["falsification_sensitivity"] == "FAILED"


def test_failing_generated_verifier_test_requires_rework(tmp_path: Path):
    admission, good, bad = setup_case(tmp_path)
    (good / "test_exit_code.txt").write_text("1", encoding="utf-8")
    (good / "verification.json").write_text(json.dumps({
        "source": "independent_p3_stdlib_oracle", "status": "FAILED",
        "sandbox_test_exit_code": 1, "sandbox_pipeline_exit_code": 0,
    }), encoding="utf-8")
    result = assess_verifier(admission=admission, positive=good, negative=bad)
    assert result["status"] == "REWORK_REQUIRED"


def test_model_wants_rework_cannot_be_ignored(tmp_path: Path):
    admission, good, bad = setup_case(tmp_path)
    data = json.loads(admission.read_text())
    data["verifier_model_next_action"] = "request_rework"
    admission.write_text(json.dumps(data), encoding="utf-8")
    result = assess_verifier(admission=admission, positive=good, negative=bad)
    assert result["status"] == "REWORK_REQUIRED"
    assert result["next_stage"] == "STOP_OR_REWORK"


def test_invented_success_with_missing_true_exit_code_fails(tmp_path: Path):
    admission, good, bad = setup_case(tmp_path)
    (good / "test_exit_code.txt").unlink()
    with pytest.raises(IndependentVerifierError, match="exit code"):
        assess_verifier(admission=admission, positive=good, negative=bad)


def test_mismatch_between_host_measured_and_oracle_codes_fails(tmp_path: Path):
    admission, good, bad = setup_case(tmp_path)
    (good / "test_exit_code.txt").write_text("2", encoding="utf-8")
    with pytest.raises(IndependentVerifierError, match="differ"):
        assess_verifier(admission=admission, positive=good, negative=bad)
