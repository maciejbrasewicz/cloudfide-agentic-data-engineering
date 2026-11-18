"""Independent standard-library profiler for the ORIGINAL CloudFide CSV.

Does not import pandas, pipeline.py, production cleaning, or any agent model.
Every reported count comes from parsing raw source bytes, not an LLM claim.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .schemas.architect import SourceFacts


_COLUMNS = (
    "Order ID", "Region", "Product", "Quantity ", "Unit Price",
    "Discount", "Order Date",
)
_QUANTITY = re.compile(r"-?\d+(?: \d{3})*\Z")
_ORDER = re.compile(r"SO-\d{5}\Z")
_AMOUNT = re.compile(r"\d+(?:[.,]\d{1,2})?\Z")
_ZERO = Decimal("0.00")


class SourceEvidenceError(ValueError):
    """The raw source is malformed or its original control totals disagree."""


def _source_file(root: Path) -> Path:
    path = root / "sales.csv"
    if path.is_symlink() or not path.is_file():
        raise SourceEvidenceError("Original sales.csv must be a regular file")
    if not path.resolve().is_relative_to(root.resolve()):
        raise SourceEvidenceError("Source file escapes its repository")
    return path


def _load_rows(root: Path) -> tuple[str, list[dict[str, str]]]:
    raw = _source_file(root).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if tuple(reader.fieldnames or ()) != _COLUMNS:
            raise SourceEvidenceError("Unexpected source columns or header order")
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise SourceEvidenceError("Unreadable original CSV") from exc
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise SourceEvidenceError("Inconsistent source CSV record width")
    return hashlib.sha256(raw).hexdigest(), rows


def _amount(text: str, *, allow_blank: bool = False) -> Decimal:
    if text == "" and allow_blank:
        return _ZERO
    if not _AMOUNT.fullmatch(text):
        raise SourceEvidenceError("Invalid monetary value in original source")
    try:
        return Decimal(text.replace(",", ".")).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise SourceEvidenceError("Unparseable amount in original source") from exc


def _quantity(text: str) -> int:
    if not _QUANTITY.fullmatch(text):
        raise SourceEvidenceError("Invalid quantity in original source")
    return int(text.replace(" ", ""))


def source_facts(root: Path) -> SourceFacts:
    """Profile and independently reconcile original rows with their TOTAL row."""
    digest, rows = _load_rows(root)
    headers = [row for row in rows if row["Order ID"] == "Order ID"]
    controls = [row for row in rows if row["Order ID"] == "TOTAL"]
    if len(controls) != 1:
        raise SourceEvidenceError("Expected exactly one TOTAL control")
    if any(row != dict(zip(_COLUMNS, _COLUMNS)) for row in headers):
        raise SourceEvidenceError("Malformed embedded header")
    if any(row[col] != "" for col in ("Region", "Product", "Unit Price", "Order Date") for row in controls):
        raise SourceEvidenceError("Malformed TOTAL metadata")
    transactions = [row for row in rows if _ORDER.fullmatch(row["Order ID"])]
    if len(transactions) + len(headers) + len(controls) != len(rows):
        raise SourceEvidenceError("Unknown source row kind")
    raw_qty = sum(_quantity(row["Quantity "]) for row in transactions)
    raw_discount = sum((_amount(row["Discount"], allow_blank=True) for row in transactions), _ZERO)
    control_qty = _quantity(controls[0]["Quantity "])
    control_discount = _amount(controls[0]["Discount"])
    if raw_qty != control_qty or raw_discount != control_discount:
        raise SourceEvidenceError("Original TOTAL disagrees before deduplication")

    seen = set()
    duplicates = 0
    for row in transactions:
        identity = tuple(row[column] for column in _COLUMNS)
        if identity in seen:
            duplicates += 1
        seen.add(identity)
        if row["Unit Price"]:
            _amount(row["Unit Price"])
    return SourceFacts(
        source_sha256=digest,
        source_rows=len(rows),
        transaction_rows=len(transactions),
        repeated_header_rows=len(headers),
        total_control_rows=len(controls),
        exact_duplicate_extra_rows=duplicates,
        missing_unit_price_rows=sum(not row["Unit Price"] for row in transactions),
        blank_discount_rows=sum(not row["Discount"] for row in transactions),
        negative_quantity_rows=sum(_quantity(row["Quantity "]) < 0 for row in transactions),
        noncanonical_region_rows=sum(
            row["Region"] != row["Region"].strip().title() for row in transactions
        ),
        comma_price_rows=sum("," in row["Unit Price"] for row in transactions),
        spaced_quantity_rows=sum(" " in row["Quantity "] for row in transactions),
        raw_quantity_total=raw_qty,
        raw_discount_total=f"{raw_discount:.2f}",
        control_quantity=control_qty,
        control_discount=f"{control_discount:.2f}",
        control_reconciled=True,
    )


def inspect_original_order_ids(root: Path, order_ids: str) -> str:
    """Read only existing, well-formed order IDs. Fail instead of returning invented rows."""
    ids = [item.strip() for item in order_ids.split(",") if item.strip()]
    if not 1 <= len(ids) <= 10 or not all(_ORDER.fullmatch(item) for item in ids):
        raise SourceEvidenceError("Specify 1 to 10 valid original order IDs")
    digest, rows = _load_rows(root)
    matches = [
        {"source_line": index + 2, **row}
        for index, row in enumerate(rows) if row["Order ID"] in ids
    ]
    if not matches:
        raise SourceEvidenceError("No original records match those IDs")
    return json.dumps({"source_sha256": digest, "rows": matches[:40]}, ensure_ascii=False)


def original_tests(root: Path) -> dict[str, str]:
    """Return only the exact employer-supplied test file, never any local implementation."""
    path = root / "test_virtual_column.py"
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise SourceEvidenceError("Original test file missing or redirected")
    data = path.read_bytes()
    if not data or len(data) > 24_000:
        raise SourceEvidenceError("Original tests unexpectedly empty or oversized")
    return {"sha256": hashlib.sha256(data).hexdigest(), "content": data.decode("utf-8")}
