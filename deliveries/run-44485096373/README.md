# Sales revenue pipeline

This project safely calculates pandas virtual columns and cleans the supplied sales export into exact regional revenue totals.

## Setup and commands

Use Python 3.11 or newer in a virtual environment, then install pandas and pytest:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install pandas pytest
```

Run the pipeline from the repository root:

```bash
python pipeline.py --input sales.csv --output revenue_by_region.csv
```

Run the complete test suite with one command:

```bash
python -m pytest
```

The output CSV has the exact columns `region,revenue`, has one row for each of Central, East, North, South, and West in that order, and writes monetary totals to two decimal places.

## Expression safety

`add_virtual_column` accepts existing column identifiers, parentheses, and binary `+`, `-`, and `*`. It parses expressions with `ast` and walks an allow-listed syntax tree; it does not use `eval` or `exec`. Invalid syntax, unsupported constructs, unknown columns, and labels containing anything other than letters or underscores return an empty DataFrame. A successful call returns a copy and does not mutate its input.

## Source findings and handling

Counts below describe the raw transaction population before duplicate removal where applicable:

| Finding | Rows | Handling |
|---|---:|---|
| Transaction records | 1,505 | Reconciled before cleaning. |
| Embedded repeated header | 1 | Recognized by `Order ID` and excluded from transactions. |
| `TOTAL` control record | 1 | Used for reconciliation, then excluded. |
| Extra exact duplicates | 5 | Removed after, never before, successful raw reconciliation. |
| Missing unit prices | 4 | Filled only when that product has exactly one observed price; otherwise the pipeline fails closed. |
| Blank discounts | 963 | Converted explicitly to zero because blank denotes no discount. |
| Negative quantities | 6 | Retained and treated as returns, reducing revenue. |
| Noncanonical region text | 15 | Trimmed and title-cased, then checked against the five known regions. |
| Comma-decimal unit prices | 7 | Parsed as decimal separators. |
| Quantities containing spaces | 4 | All whitespace removed before strict integer parsing. |

Before exact duplicates are removed, parsed transaction quantities must sum to **37,150** and discounts to **65,924.67**, matching the source `TOTAL` row. A mismatch stops processing. Numeric parsing is strict and money is represented with `Decimal`; binary floating-point arithmetic is not used for revenue.

Revenue for every retained line is calculated through `add_virtual_column` as:

```text
Quantity * Unit_Price - Discount
```

## Assumptions and risks

* The five fully identical extra rows are export duplicates rather than legitimate repeated order lines. If they are legitimate, removing them understates revenue.
* Negative quantities represent returns and should reduce revenue. The file itself does not prove that interpretation.
* A missing price may use the sole price observed for the same product. Even a unique observed price might be historically or contractually inappropriate.
* Trimming and title-casing is sufficient for the observed region variants. Unknown values are not guessed and cause a failure.
* Dates must use `YYYY-MM-DD`; malformed records are rejected rather than silently coerced.
* Product names are trimmed for use and price inference. Ambiguous, absent, nonnumeric, or non-finite values fail closed.
