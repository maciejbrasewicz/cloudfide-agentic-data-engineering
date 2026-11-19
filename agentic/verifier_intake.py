"""Verify independent Verifier source and exact P5 candidate before sandbox use."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .candidate_intake import verify_and_stage_candidate
from .delivery_status import ROUNDS
from .verifier_gate import (
    REQUIRED_TOOLS, TEST_PATH, candidate_manifest_digest, validate_adversarial_test,
)


class VerifierAdmissionError(ValueError):
    """P4 evidence or submitted test was not independently verified."""


def _json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise VerifierAdmissionError("Expected a JSON object")
    return payload


def stage_adversarial_test(*, artifacts: Path, original: Path, destination: Path) -> dict:
    state = _json(artifacts / "p5-bounded-run-state/run_state.json")
    iteration = state.get("accepted_for_verification_iteration")
    if state.get("status") != "WAITING_VERIFIER" or type(iteration) is not int or not 1 <= iteration <= 3:
        raise VerifierAdmissionError("No P5-approved candidate for independent Verifier")
    candidate_label, sandbox_label = ROUNDS[iteration - 1]
    candidate = artifacts / candidate_label
    sandbox = artifacts / sandbox_label
    verifier = artifacts / "p4-verifier-evidence"
    gate = _json(verifier / "verifier_gate.json")
    report = _json(verifier / "verifier_report.json")
    if gate.get("status") != "PENDING_ADVERSARIAL_EXECUTION" or gate.get("failures"):
        raise VerifierAdmissionError("Verifier tool/contract gate was not passed")
    if not REQUIRED_TOOLS.issubset(set(gate.get("verified_tool_calls", []))):
        raise VerifierAdmissionError("Verifier mandatory tools were not executed")

    staged = verify_and_stage_candidate(
        archive_path=candidate / "candidate_bundle.zip",
        engineer_gate=_json(candidate / "engineer_gate.json"),
        validation_request=_json(candidate / "validation_request.json"),
        original_checkout=original, destination=destination,
    )
    candidate_sha = candidate_manifest_digest(staged["files"])
    if gate.get("candidate_manifest_sha256") != candidate_sha or report.get("candidate_manifest_sha256") != candidate_sha:
        raise VerifierAdmissionError("Verifier references another candidate SHA")

    p3_raw = (sandbox / "verification.json").read_bytes()
    receipt = json.loads(p3_raw.decode("utf-8"))
    p3_sha = hashlib.sha256(p3_raw).hexdigest()
    if receipt.get("status") != "PASSED" or receipt.get("reconciliation") != "passed":
        raise VerifierAdmissionError("P3 candidate is not independently accepted")
    if report.get("p3_receipt_sha256") != p3_sha:
        raise VerifierAdmissionError("Verifier references another P3 receipt")
    if report.get("original_test_sha256") != staged["protected_hashes"]["test_virtual_column.py"]:
        raise VerifierAdmissionError("Verifier references altered employer tests")

    submitted = verifier / TEST_PATH
    if submitted.is_symlink() or not submitted.is_file():
        raise VerifierAdmissionError("Verifier generated test missing")
    contents = submitted.read_text(encoding="utf-8")
    test_sha = validate_adversarial_test(contents)
    if gate.get("proposed_test_sha256") != test_sha or report.get("proposed_test_sha256") != test_sha:
        raise VerifierAdmissionError("Verifier test SHA differs from its actual source")
    destination_file = destination / TEST_PATH
    if destination_file.exists() or destination_file.is_symlink():
        raise VerifierAdmissionError("Candidate illegally collides with verifier-only test")
    destination_file.parent.mkdir(exist_ok=True)
    destination_file.write_text(contents, encoding="utf-8", newline="\n")
    return {
        "schema_version": 1, "status": "ADMITTED_FOR_INDEPENDENT_ADVERSARIAL_TEST",
        "iteration": iteration, "candidate_manifest_sha256": candidate_sha,
        "p3_receipt_sha256": p3_sha, "verifier_test_sha256": test_sha,
        "original_test_sha256": staged["protected_hashes"]["test_virtual_column.py"],
        "verifier_model_next_action": report.get("next_action"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Admit real Verifier tests with SHA provenance")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = stage_adversarial_test(
        artifacts=args.artifacts, original=args.original, destination=args.destination,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"], "iteration": receipt["iteration"],
        "test_sha256": receipt["verifier_test_sha256"],
    }))


if __name__ == "__main__":
    main()
