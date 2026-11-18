"""Regression tests derived from verified, reproducible Foundry review findings."""

import pandas as pd
import pytest

from contracts import read_policy
from pipeline import DataQualityError, ROOT, clean_sales


def raw_sales():
    return pd.read_csv(ROOT / "sales.csv", dtype=str, keep_default_na=False)


def test_only_identical_raw_lines_are_deduplicated():
    raw = raw_sales()
    duplicate = raw.index[raw.duplicated(keep="first")][0]
    raw.loc[duplicate, "Product"] = " " + raw.loc[duplicate, "Product"]

    cleaned, audit = clean_sales(raw)

    assert audit["exact_duplicates_removed"] == 4
    assert len(cleaned) == 1501


def test_strict_region_policy_rejects_source_whitespace():
    policy = read_policy(ROOT / "contracts/data_policy.json").model_copy(update={"region": "strict"})
    with pytest.raises(DataQualityError, match="strict policy"):
        clean_sales(raw_sales(), policy)


def test_malformed_embedded_header_fails_closed():
    raw = raw_sales()
    raw.loc[raw["Order ID"] == "Order ID", "Product"] = "INJECTED"
    with pytest.raises(DataQualityError, match="Malformed repeated header"):
        clean_sales(raw)


def test_malformed_total_metadata_fails_closed():
    raw = raw_sales()
    raw.loc[raw["Order ID"] == "TOTAL", "Region"] = "North"
    with pytest.raises(DataQualityError, match="Malformed TOTAL"):
        clean_sales(raw)
