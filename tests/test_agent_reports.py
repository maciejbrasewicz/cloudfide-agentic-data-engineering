import json

import pytest
from pydantic import ValidationError

from agentic.models import parse_report


def test_agent_output_must_match_schema():
    valid = {
        "role": "data_architect",
        "summary": "Prices are missing on some source lines.",
        "findings": [{
            "category": "source_data", "severity": "high",
            "statement": "A missing reference price may be ambiguous.",
            "evidence": "The source includes empty unit-price cells.",
            "suggested_verification": "Check distinct prices for each product",
        }],
        "recommended_next_action": "Test an ambiguous price case",
    }
    assert parse_report(json.dumps(valid)).role == "data_architect"
    valid["dangerous_extra_tool_call"] = "run_anything"
    with pytest.raises(ValidationError):
        parse_report(json.dumps(valid))
