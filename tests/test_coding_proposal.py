"""Safe, human-gated autonomous code generation boundaries."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic.coding_proposal import CodeProposal, parse_proposal, validate_content


GOOD = {
    "kind": "new_regression_test",
    "file_path": "tests/test_agent_generated_regression.py",
    "code": (
        "import pandas as pd\n"
        "from solution import add_virtual_column\n\n"
        "def test_model_proposed_invalid_expression_returns_empty_frame():\n"
        "    source = pd.DataFrame({'x': [1], 'y': [2]})\n"
        "    result = add_virtual_column(source, 'x / y', 'z')\n"
        "    assert result.empty\n"
    ),
    "rationale": "A forbidden division expression must fail closed by the task contract.",
    "test_claim": "Invalid division is rejected without modifying the input frame.",
}


def test_model_can_propose_a_real_python_test_in_empty_isolation(tmp_path):
    proposal = CodeProposal.model_validate(GOOD)
    saved = validate_content(proposal, tmp_path)
    assert saved.is_file()
    assert saved.read_text(encoding="utf-8") == GOOD["code"]
    assert "test_" in saved.name


def test_model_cannot_overwrite_an_existing_generated_test(tmp_path):
    proposal = CodeProposal.model_validate(GOOD)
    validate_content(proposal, tmp_path)
    with pytest.raises(ValueError, match="existing"):
        validate_content(proposal, tmp_path)


@pytest.mark.parametrize("patch", [
    {"file_path": "pipeline.py"},
    {"file_path": ".github/workflows/ci.yml"},
    {"kind": "code_execution"},
    {"rationale": "tiny"},
    {"arbitrary_field": "untrusted"},
])
def test_model_cannot_change_target_or_escape_contract(patch):
    request = dict(GOOD)
    request.update(patch)
    with pytest.raises(ValidationError):
        CodeProposal.model_validate(request)


def test_must_contain_a_real_test_function(tmp_path):
    request = dict(GOOD)
    request["code"] = "import pandas as pd\n\n" + "def not_a_test():\n    return 3\n" * 7
    proposal = CodeProposal.model_validate(request)
    with pytest.raises(ValueError, match="test function"):
        validate_content(proposal, tmp_path)


def test_invalid_python_cannot_be_submitted(tmp_path):
    request = dict(GOOD)
    request["code"] = "def test_bad(:\n" * 20
    with pytest.raises(SyntaxError):
        validate_content(CodeProposal.model_validate(request), tmp_path)
