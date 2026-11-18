"""Property tests over varied values rather than a few hand-picked examples."""
from decimal import Decimal

import pandas as pd
from hypothesis import given, settings, strategies as st

from solution import add_virtual_column


@settings(max_examples=100)
@given(
    quantities=st.lists(st.integers(min_value=-1000, max_value=1000), min_size=1, max_size=20),
    prices=st.integers(min_value=0, max_value=100_000),
    discounts=st.integers(min_value=0, max_value=1000),
)
def test_decimal_expression_matches_independent_integer_cents(quantities, prices, discounts):
    price = Decimal(prices) / 100
    discount = Decimal(discounts) / 100
    frame = pd.DataFrame({
        "quantity": quantities,
        "unit_price": [price] * len(quantities),
        "discount": [discount] * len(quantities),
    })
    result = add_virtual_column(frame, "quantity*unit_price-discount", "revenue")
    expected = [Decimal(q * prices - discounts) / 100 for q in quantities]
    assert result.revenue.tolist() == expected
    assert "revenue" not in frame.columns
