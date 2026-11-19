# Sales revenue pipeline

This project contains a restricted arithmetic helper for pandas and a deterministic cleaning pipeline for the supplied sales export. Financial values use `Decimal` during calculation and aggregation.

## Setup and commands

Python 3.11 or newer is recommended. Create a virtual environment, then install the runtime and test dependencies:

```bash
python -m pip install pandas pytest
```

Run all tests from the repository root:

```bash
python -m pytest
```

Run the pipeline with its default paths:

```bash
python pipeline.py
```

Or provide paths explicitly:

```bash
python pipeline.py --input sales.csv --output revenue_by_region.csv
```

The generated CSV has exactly two columns, `region` and `revenue`, and is sorted by region.

## Expression behavior

`add_virtual_column` accepts column labels made only from ASCII letters and underscores. Expressions may use existing labels, parentheses, and binary `+`, `-`, and `*`, with normal precedence and surrounding whitespace. A restricted syntax tree is parsed and walked without `eval` or `exec`. Invalid syntax, labels, operators, or references produce an empty DataFrame. Valid calls return a copy and do not mutate the input.

## Source controls and cleaning

The inspected export contains 1,507 data rows: 1,505 transactions, one repeated header, and one `TOTAL` control row. Before exclusions or deduplication, the pipeline sums the untouched transaction population. Its quantity of **37,150** and discount of **65,924.67** must match the `TOTAL` row; otherwise processing stops.

After that reconciliation, the measured issues are handled as follows:

| Issue | Affected rows | Treatment |
|---|---:|---|
| Repeated header | 1 | Recognize as metadata and exclude. |
| `TOTAL` summary | 1 | Exclude only after raw controls reconcile. |
| Extra exact duplicate rows | 5 | Keep the first exact row and remove extras after reconciliation. |
| Missing unit price | 4 | Fill only when the product has exactly one observed usable price; otherwise fail. |
| Blank discount | 963 | Convert to exact zero, as an empty discount means no discount. |
| Negative quantity | 6 | Retain the sign and calculate it as a return. |
| Noncanonical region text | 15 | Strip surrounding whitespace and apply title case. |
| Comma decimal unit price | 7 | Accept comma as the decimal separator; values containing both separators fail. |
| Quantity containing spaces | 4 | Remove spaces before requiring an integer. |

Dates must use `YYYY-MM-DD`, and required text fields cannot be blank. Unknown row types, malformed numeric values, unexpected regions, control failures, and ambiguous price repairs raise `DataQualityError` rather than silently dropping data.

Revenue is added through `add_virtual_column` using `quantity * unit_price - discount`. It is then summed for Central, East, North, South, and West.

## Assumptions and risks

Removing exact duplicates is an **unverified business assumption**: identical records might be legitimate order lines, in which case revenue would be understated. Treating the six negative quantities as returns is also unverified; if they are corrections or errors, signed revenue may be inappropriate. Applying a product's unique observed price to a missing-price row assumes that price remains valid across date, region, and commercial terms. The source does not prove that assumption, so multiple candidate prices cause a closed failure. Region stripping and title casing assumes the variants are formatting errors rather than distinct business labels.

These choices follow the supplied data policy, retain repairable rows, and fail when a deterministic repair cannot be made.
