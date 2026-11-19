"""P4 independent host gate: executable verifier test must detect a known mutation.

No model can declare its own tests successful; two actual sandbox executions
and a fresh independent P3 financial oracle receipt are the only evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class IndependentVerifierError(ValueError):
    """Adversarial receipts are inconsistent or not present."""


def _json(path: Path) -> dict:
    item = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(item, dict):
        raise IndependentVerifierError("Expected an object receipt")
    return item


def _exit_code(path: Path) -> int:
    try:
        result = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        raise IndependentVerifierError("Missing measured sandbox exit code") from exc
    if not 0 <= result <= 255:
        raise IndependentVerifierError("Measured exit code out of valid range")
    return result


def assess_verifier(*, admission: Path, positive: Path, negative: Path) -> dict:
    evidence = _json(admission)
    good = _json(positive / "verification.json")
    if evidence.get("status") != "ADMITTED_FOR_INDEPENDENT_ADVERSARIAL_TEST":
        raise IndependentVerifierError("Verifier test not admitted on original source")
    if good.get("source") != "independent_p3_stdlib_oracle":
        raise IndependentVerifierError("Positive run not verified by independent oracle")
    positive_pytest = _exit_code(positive / "test_exit_code.txt")
    positive_pipeline = _exit_code(positive / "pipeline_exit_code.txt")
    negative_pytest = _exit_code(negative / "test_exit_code.txt")
    if positive_pytest != good.get("sandbox_test_exit_code") or positive_pipeline != good.get("sandbox_pipeline_exit_code"):
        raise IndependentVerifierError("Positive exit codes differ from trusted oracle receipt")
    if not (positive / "tests.log").is_file() or not (negative / "tests.log").is_file():
        raise IndependentVerifierError("Actual independent test execution logs missing")

    errors: list[str] = []
    if positive_pytest != 0 or positive_pipeline != 0 or good.get("status") != "PASSED":
        errors.append("New Verifier tests or independent revenue oracle failed on real candidate")
    if negative_pytest == 0:
        errors.append("Verifier test failed to catch deliberately broken add_virtual_column")
    if evidence.get("verifier_model_next_action") == "request_rework":
        errors.append("Verifier explicitly requested code review/rework")
    if errors:
        status = "WEAK_VERIFIER_TEST" if negative_pytest == 0 else "REWORK_REQUIRED"
    else:
        status = "PASSED"
    return {
        "schema_version": 1, "source": "independent_p4_dual_sandbox_verification",
        "status": status,
        "iteration": evidence.get("iteration"),
        "candidate_manifest_sha256": evidence.get("candidate_manifest_sha256"),
        "verifier_test_sha256": evidence.get("verifier_test_sha256"),
        "positive_test_exit_code": positive_pytest,
        "positive_pipeline_exit_code": positive_pipeline,
        "negative_mutation_test_exit_code": negative_pytest,
        "independent_p3_status": good.get("status"),
        "positive_oracle_sha256": hashlib.sha256(
            (positive / "verification.json").read_bytes()
        ).hexdigest(),
        "falsification_sensitivity": "PASSED" if negative_pytest != 0 else "FAILED",
        "failures": errors,
        "next_stage": "P6_DRAFT_PR_REVIEW" if status == "PASSED" else "STOP_OR_REWORK",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify real independent P4 test outcomes")
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--positive", type=Path, required=True)
    parser.add_argument("--negative", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = assess_verifier(
            admission=args.admission, positive=args.positive, negative=args.negative,
        )
    except (IndependentVerifierError, OSError, ValueError, KeyError) as exc:
        receipt = {
            "schema_version": 1, "source": "independent_p4_dual_sandbox_verification",
            "status": "INFRA_FAILURE", "failures": [str(exc)],
            "next_stage": "STOP_OR_REWORK",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"], "failures": receipt.get("failures"),
    }))
    if receipt["status"] != "PASSED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
