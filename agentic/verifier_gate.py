"""Do not trust model claims: verify actual Verifier tool execution and test bytes."""
from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from .schemas.verifier import VerificationGate, VerificationReport

TEST_PATH = "tests/test_verifier_generated.py"
MAX_TEST_BYTES = 12_000
REQUIRED_TOOLS = frozenset({
    "read_spec", "read_original_tests", "read_approved_policy",
    "read_candidate_file", "read_p3_receipt",
    "write_adversarial_test", "request_independent_validation",
})
REQUIRED_CANDIDATE_READS = frozenset({"solution.py", "pipeline.py"})


class VerifierPolicyError(ValueError):
    """Untrusted verifier attempted to submit an unsafe or useless test."""


@dataclass
class VerifierLedger:
    calls: list[str] = field(default_factory=list)
    inspected_candidates: set[str] = field(default_factory=set)
    test_source: str | None = None
    test_sha256: str | None = None
    validation_requested: bool = False

    def record(self, tool: str, *, candidate_path: str | None = None) -> None:
        if tool not in REQUIRED_TOOLS:
            raise ValueError("Unexpected Verifier tool name")
        self.calls.append(tool)
        if tool == "read_candidate_file" and candidate_path:
            self.inspected_candidates.add(candidate_path)


def validate_adversarial_test(source: str) -> str:
    """Syntax and minimal executable assertion controls; no code executed here."""
    if not isinstance(source, str) or not source or "\x00" in source or "\r" in source:
        raise VerifierPolicyError("Verifier test must be normalized nonempty UTF-8")
    raw = source.encode("utf-8")
    if len(raw) > MAX_TEST_BYTES:
        raise VerifierPolicyError("Verifier test is too large")
    try:
        tree = ast.parse(source, filename=TEST_PATH)
    except (SyntaxError, ValueError) as exc:
        raise VerifierPolicyError("Verifier submitted invalid Python syntax") from exc
    tests = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    if not tests:
        raise VerifierPolicyError("At least one direct test_* function is required")
    if not any(
        isinstance(node, ast.Assert)
        or (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "raises"
        )
        for test in tests for node in ast.walk(test)
    ):
        raise VerifierPolicyError("Verifier tests need at least one executable assertion")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"skip", "skipif", "xfail"}:
                raise VerifierPolicyError("Verifier cannot submit a skipped or xfail test")
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            for decorator in node.decorator_list:
                if "skip" in ast.unparse(decorator) or "xfail" in ast.unparse(decorator):
                    raise VerifierPolicyError("Verifier cannot mark tests as skipped")
    return hashlib.sha256(raw).hexdigest()


def candidate_manifest_digest(files: list[dict]) -> str:
    payload = json.dumps(
        sorted(files, key=lambda entry: entry["path"]),
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evaluate_verifier(
    *, report: VerificationReport, ledger: VerifierLedger,
    actual_candidate_digest: str, actual_p3_digest: str,
    original_tests_sha256: str,
) -> VerificationGate:
    failures: list[str] = []
    missing = REQUIRED_TOOLS - set(ledger.calls)
    if missing:
        failures.append("Required Verifier tool calls not executed: " + ", ".join(sorted(missing)))
    if REQUIRED_CANDIDATE_READS - ledger.inspected_candidates:
        failures.append("Verifier did not inspect both candidate implementations")
    if report.candidate_manifest_sha256 != actual_candidate_digest:
        failures.append("Candidate manifest digest not anchored to inspected source")
    if report.p3_receipt_sha256 != actual_p3_digest:
        failures.append("P3 reconciliation evidence hash does not match")
    if report.original_test_sha256 != original_tests_sha256:
        failures.append("Employer test SHA does not match trusted original")
    if not ledger.test_source or not ledger.test_sha256:
        failures.append("Verifier did not create an actual independent test")
        verified_test = "0" * 64
    else:
        try:
            verified_test = validate_adversarial_test(ledger.test_source)
        except VerifierPolicyError:
            verified_test = "0" * 64
            failures.append("Submitted Verifier test failed source validation")
    if verified_test != report.proposed_test_sha256 or verified_test != ledger.test_sha256:
        failures.append("Verifier reported a different test hash than actual source")
    if not ledger.validation_requested:
        failures.append("Verifier did not request separate execution of its test")
    return VerificationGate(
        status="INCOMPLETE" if failures else "PENDING_ADVERSARIAL_EXECUTION",
        candidate_manifest_sha256=actual_candidate_digest,
        proposed_test_sha256=verified_test,
        verified_tool_calls=list(ledger.calls),
        failures=failures,
    )
