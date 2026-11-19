# Sales revenue pipeline

This project safely derives pandas virtual columns and cleans the supplied sales export into exact regional revenue totals.

## Setup

Use Python 3.10 or newer. From the project directory, create an isolated environment and install pandas and pytest:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install pandas pytest
```

## Run

Generate the regional output with explicit paths:

```bash
python pipeline.py --input sales.csv --output revenue_by_region.csv
```

The backward-compatible positional form also works:

```bash
python pipeline.py sales.csv revenue_by_region.csv
```

Run all employer and project tests with one command:

```bash
python -m pytest
```

## Virtual-column safety

`add_virtual_column` parses expressions with Python's AST parser but does not use `eval` or `exec`. It accepts only existing letter-and-underscore column names joined by binary `+`, `-`, and `*`. Constants, calls, attributes, indexing, unary operators, unknown names, malformed syntax, duplicate labels, invalid labels, and overwriting an existing column are rejected with a new empty DataFrame. Valid calls return a copy and do not mutate the caller's frame.

## Source findings and handling

Counts below are measured on raw transaction rows, before exact-duplicate removal, because the `TOTAL` control describes the raw export.

| Finding | Rows | Handling |
|---|---:|---|
| Repeated header inside the data | 1 | Identify by all seven field values and remove after control reconciliation. |
| `TOTAL` summary/control | 1 | Verify its quantity and discount totals, then exclude it from transactions. |
| Exact duplicate extra rows | 5 | Remove only exact duplicates after reconciliation, keeping the first row. |
| Missing unit price | 4 | Fill only from the product's single unique observed price; otherwise fail. |
| Blank discount | 963 | Convert to exact zero, as a blank means no discount. |
| Negative quantity | 6 | Retain as returns so they reduce revenue. |
| Noncanonical region formatting | 15 | Strip surrounding whitespace and title-case; reject unknown regions. |
| Comma decimal unit price | 7 | Accept comma as the decimal separator. Mixed comma-and-dot values fail. |
| Spaces in quantity | 4 | Remove spaces, then require an integer. |

The raw 1,505 transaction rows reconcile to the source control before deduplication: quantity `37150` and discount `65924.67`. The export also contains the header and control rows, for 1,507 data rows read by pandas.

## Calculation and assumptions

All quantities, prices, discounts, line revenues, and regional sums use `Decimal`; conversion through binary floating point is avoided. Revenue is calculated through `add_virtual_column` as:

```text
quantity * unit_price - discount
```

The output contains exactly `Central`, `East`, `North`, `South`, and `West` in deterministic order, with revenue formatted to two decimal places.

The following approved cleaning choices are business assumptions rather than facts proven by the export:

- the five exact duplicate extras are export duplication rather than legitimate repeated lines;
- negative quantities represent returns, with the recorded discount still used by the same formula;
- a unique observed price for a product is suitable for its missing historical prices;
- trimming and title-casing is the intended mapping for region variants.

The pipeline fails closed when a control does not reconcile, a missing price has zero or multiple candidates, a numeric value is malformed or ambiguous, a date is invalid, an order identifier conflicts after deduplication, or a normalized region is outside the five expected regions.
