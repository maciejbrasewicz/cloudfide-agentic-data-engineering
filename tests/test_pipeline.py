from decimal import Decimal

import pandas as pd
import pytest

from pipeline import DataQualityError, ROOT, clean_sales, run_pipeline


@pytest.fixture
def source_df():
    return pd.read_csv(ROOT / "sales.csv", dtype=str, keep_default_na=False)


def test_source_controls_and_repairs(source_df):
    cleaned, report = clean_sales(source_df)
    assert report["source_rows"] == 1507
    assert report["transactions_before_dedup"] == 1505
    assert report["exact_duplicates_removed"] == 5
    assert report["transactions_after_dedup"] == 1500
    assert report["repeated_headers"] == 1
    assert report["total_control_rows"] == 1
    assert report["raw_control_quantity"] == 37150
    assert report["raw_control_discount"] == "65924.67"
    assert report["comma_decimal_prices"] == 7
    assert report["spaced_quantities"] == 4
    assert report["regions_normalized"] == 15
    assert report["missing_unit_prices_recovered"] == 4
    assert report["negative_quantities_retained"] == 6
    assert len(cleaned) == 1500
    assert all(isinstance(x, Decimal) for x in cleaned.revenue)


def test_independent_decimal_reconciliation(source_df):
    cleaned, _ = clean_sales(source_df)
    independently_calculated = sum(
        (Decimal(int(row.quantity)) * row.unit_price - row.discount for row in cleaned.itertuples()),
        Decimal("0.00"),
    )
    assert independently_calculated == Decimal("2570247.03")
    assert sum(cleaned.revenue, Decimal("0.00")) == independently_calculated


def test_expected_region_totals(tmp_path):
    result_file = tmp_path / "revenue_by_region.csv"
    report = run_pipeline(ROOT / "sales.csv", result_file, None, ROOT / "contracts" / "data_policy.json")
    result = pd.read_csv(result_file, dtype=str)
    assert dict(zip(result.region, result.revenue, strict=True)) == {
        "Central": "515824.67", "East": "442219.91", "North": "665897.52",
        "South": "504036.04", "West": "442268.89",
    }
    assert report["net_revenue"] == "2570247.03"
    assert result_file.read_bytes() == (ROOT / "revenue_by_region.csv").read_bytes()


def test_reject_broken_source_control(source_df):
    bad = source_df.copy()
    bad.loc[0, "Quantity "] = "999"
    with pytest.raises(DataQualityError, match="TOTAL mismatch"):
        clean_sales(bad)


def test_fail_closed_on_ambiguous_missing_price(source_df):
    bad = source_df.copy()
    bad.loc[bad["Order ID"] == "SO-10012", "Unit Price"] = "199.00"
    with pytest.raises(DataQualityError, match="Ambiguous missing price"):
        clean_sales(bad)


def test_unknown_region_rejected(source_df):
    bad = source_df.copy()
    bad.loc[bad["Order ID"] == "SO-10001", "Region"] = "Atlantis"
    with pytest.raises(DataQualityError, match="Unknown region"):
        clean_sales(bad)


def test_quantity_never_silently_dropped(source_df):
    bad = source_df.copy()
    bad.loc[bad["Order ID"] == "SO-10001", "Quantity "] = "??"
    with pytest.raises(DataQualityError, match="quantity"):
        clean_sales(bad)
