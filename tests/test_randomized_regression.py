"""Dependency-free randomized cross-check of the vectorized expression engine."""
import random
from decimal import Decimal

import pandas as pd

from solution import add_virtual_column


def test_many_random_decimal_inputs():
    randomizer = random.Random(20261118)
    for _ in range(150):
        quantities = [randomizer.randint(-50, 500) for _ in range(8)]
        price_cents = randomizer.randint(0, 250_000)
        discount_cents = randomizer.randint(0, 1000)
        frame = pd.DataFrame({
            "quantity": quantities,
            "unit_price": [Decimal(price_cents) / 100] * len(quantities),
            "discount": [Decimal(discount_cents) / 100] * len(quantities),
        })
        result = add_virtual_column(frame, "quantity * unit_price - discount", "revenue")
        assert result.revenue.tolist() == [
            Decimal(quantity * price_cents - discount_cents) / 100
            for quantity in quantities
        ]
