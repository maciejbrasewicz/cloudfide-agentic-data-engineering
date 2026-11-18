"""Demonstrate that policy values alter execution, not just validate a JSON file."""

import pandas as pd
import pytest
from pydantic import ValidationError

from contracts import DataPolicy, read_policy
from pipeline import DataQualityError, ROOT, clean_sales


@pytest.fixture
def raw():
    return pd.read_csv(ROOT / "sales.csv", dtype=str, keep_default_na=False)


@pytest.fixture
def approved():
    return read_policy(ROOT / "contracts/data_policy.json")


def decision(policy: DataPolicy, **updates: str) -> DataPolicy:
    return DataPolicy.model_validate({**policy.model_dump(), **updates})


def test_contract_actually_controls_deduplication(raw, approved):
    cleaned, report = clean_sales(raw, decision(approved, duplicates="keep_all"))
    assert report["exact_duplicates_removed"] == 0
    assert len(cleaned) == 1505


@pytest.mark.parametrize("update, expected", [
    ({"missing_discount": "fail"}, "Blank discounts rejected"),
    ({"missing_unit_price": "fail"}, "Missing unit prices rejected"),
    ({"negative_quantity": "reject"}, "Negative quantities rejected"),
    ({"region": "strict"}, "Unknown region"),
])
def test_strict_contract_stops_unapproved_repairs(raw, approved, update, expected):
    with pytest.raises(DataQualityError, match=expected):
        clean_sales(raw, decision(approved, **update))


def test_unknown_policy_command_cannot_be_injected(approved):
    with pytest.raises(ValidationError):
        decision(approved, missing_unit_price="python:exec('bad')")
