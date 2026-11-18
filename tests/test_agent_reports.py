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

@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("implementation", "pipeline"),
        ("tests", "testing"),
        ("policy", "spec"),
        ("output", "pipeline"),
        ("data_quality", "source_data"),
    ],
)
def test_known_agent_taxonomy_synonyms_are_canonicalized(alias, expected):
    report = {
        "role": "verification_engineer",
        "summary": "Independent evidence and verified observations.",
        "findings": [{
            "category": alias,
            "severity": "medium",
            "statement": "The agent found a relevant engineering observation.",
            "evidence": "Tool output includes verifiable supporting details.",
            "suggested_verification": "Check the source with the deterministic tests.",
        }],
        "recommended_next_action": "Investigate the referenced observation.",
    }
    parsed = parse_report(json.dumps(report))
    assert parsed.findings[0].category == expected


def test_unknown_agent_category_remains_rejected():
    report = {
        "role": "data_engineer",
        "summary": "A reviewer returned an unrecognized category.",
        "findings": [{
            "category": "magical_future_guess",
            "severity": "high",
            "statement": "A made-up category cannot bypass validation.",
            "evidence": "The value is not on the reviewed allowlist.",
            "suggested_verification": "Reject this output deterministically.",
        }],
        "recommended_next_action": "Reject unrecognized categories.",
    }
    with pytest.raises(ValidationError):
        parse_report(json.dumps(report))
