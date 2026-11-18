"""Validated, versioned data decisions applied by the deterministic ETL."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DataPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    source_control: Literal["verify_before_deduplication"]
    header_rows: Literal["remove_repeated_header"]
    summary_rows: Literal["exclude_after_reconciliation"]
    duplicates: Literal["remove_exact_duplicates", "keep_all"]
    region: Literal["strip_and_title_case", "strict"]
    decimal_separator: Literal["accept_dot_or_comma"]
    quantity_separator: Literal["strip_spaces"]
    missing_discount: Literal["zero", "fail"]
    missing_unit_price: Literal["unique_price_per_product_or_fail", "fail"]
    negative_quantity: Literal["retain_as_returns", "reject"]
    ambiguous_data: Literal["fail_closed"]


def read_policy(path: Path) -> DataPolicy:
    """Parse before any output write; unknown policies always fail validation."""
    return DataPolicy.model_validate(json.loads(path.read_text(encoding="utf-8")))
