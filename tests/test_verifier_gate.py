"""P4 verifier must submit a REAL executable falsification test, not a JSON claim."""
from __future__ import annotations

import hashlib

import pytest

from agentic.schemas.verifier import VerificationReport
from agentic.verifier_gate import (
    REQUIRED_TOOLS, TEST_PATH, VerifierLedger, VerifierPolicyError,
    candidate_manifest_digest, evaluate_verifier, validate_adversarial_test,
)


CANDIDATE_SHA = "1" * 64
P3_SHA = "2" * 64
ORIGINAL_SHA = "3" * 64
TEST = (
    "import pandas as pd\n"
    "from solution import add_virtual_column\n\n"
    "def test_real_arithmetic_not_just_function_existence():\n"
    "    source = pd.DataFrame({'a': [2], 'b': [3]})\n"
    "    result = add_virtual_column(source, 'a + b', 'total')\n"
    "    assert result.at[0, 'total'] == 5\n"
)


def report(test_sha: str | None = None) -> VerificationReport:
    return VerificationReport(
        role="verification_engineer",
        candidate_manifest_sha256=CANDIDATE_SHA,
        p3_receipt_sha256=P3_SHA,
        overall_assessment="Independent adversarial review of the actual implementation.",
        tested_assumption="Arithmetic virtual column must produce a nonempty, correct result.",
        expected_failure_mode="A broken implementation returning an empty frame fails the test.",
        original_test_sha256=ORIGINAL_SHA,
        proposed_test_sha256=test_sha or validate_adversarial_test(TEST),
        risk_notes=[
            "Data policy assumptions remain subject to domain confirmation.",
            "Passing a test is not proof that all conceivable edge cases are handled.",
        ],
        next_action="request_independent_test",
    )


def ledger() -> VerifierLedger:
    value = VerifierLedger()
    for name in sorted(REQUIRED_TOOLS):
        value.record(name)
    value.inspected_candidates.update({"solution.py", "pipeline.py"})
    value.test_source = TEST
    value.test_sha256 = validate_adversarial_test(TEST)
    value.validation_requested = True
    return value


def evaluate(value: VerificationReport, actions: VerifierLedger):
    return evaluate_verifier(
        report=value, ledger=actions,
        actual_candidate_digest=CANDIDATE_SHA,
        actual_p3_digest=P3_SHA, original_tests_sha256=ORIGINAL_SHA,
    )


def test_real_test_and_all_real_tools_required():
    result = evaluate(report(), ledger())
    assert result.status == "PENDING_ADVERSARIAL_EXECUTION"
    assert not result.failures
    assert set(result.verified_tool_calls) == REQUIRED_TOOLS
    assert result.proposed_test_sha256 == hashlib.sha256(TEST.encode()).hexdigest()


@pytest.mark.parametrize("missing", sorted(REQUIRED_TOOLS))
def test_missing_real_tool_cannot_be_hidden_by_model_json(missing: str):
    actions = ledger()
    actions.calls = [name for name in actions.calls if name != missing]
    result = evaluate(report(), actions)
    assert result.status == "INCOMPLETE"
    assert any("not executed" in failure for failure in result.failures)


def test_reading_only_one_candidate_file_is_incomplete():
    actions = ledger()
    actions.inspected_candidates.remove("pipeline.py")
    result = evaluate(report(), actions)
    assert result.status == "INCOMPLETE"
    assert any("both candidate" in failure for failure in result.failures)


def test_invented_hash_and_missing_test_are_rejected():
    actions = ledger()
    actions.test_source = None
    actions.test_sha256 = None
    result = evaluate(report("f" * 64), actions)
    assert result.status == "INCOMPLETE"
    assert any("actual independent test" in failure for failure in result.failures)


def test_unbound_receipts_cannot_pass():
    proposal = report()
    proposal.p3_receipt_sha256 = "0" * 64
    result = evaluate(proposal, ledger())
    assert result.status == "INCOMPLETE"
    assert any("P3 reconciliation" in failure for failure in result.failures)


@pytest.mark.parametrize("source", [
    "import pandas as pd\n",  # No test
    "def test_empty():\n    return None\n",  # No assertion
    "def test_foo(:\n    assert True\n",  # Invalid syntax
    "import pytest\n@pytest.mark.skip\ndef test_foo():\n    assert True\n",
    "import pytest\ndef test_foo():\n    pytest.skip('incomplete')\n    assert True\n",
    "def test_foo():\n    assert True\n" + "x" * 12_500,
])
def test_empty_skipped_useless_or_malformed_adversarial_tests_rejected(source: str):
    with pytest.raises(VerifierPolicyError):
        validate_adversarial_test(source)


def test_candidate_digest_independent_of_file_order():
    one = [{"path": "solution.py", "sha256": "a" * 64}, {"path": "pipeline.py", "sha256": "b" * 64}]
    assert candidate_manifest_digest(one) == candidate_manifest_digest(list(reversed(one)))


def test_verifier_file_path_is_separate_from_model_written_tests():
    assert TEST_PATH == "tests/test_verifier_generated.py"
    assert validate_adversarial_test(TEST)
