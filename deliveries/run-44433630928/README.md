# Sales virtual-column pipeline

This project implements a restricted arithmetic virtual-column function and a deterministic pandas pipeline for the supplied sales export.

## Setup and commands

Use Python 3.10 or newer. In a virtual environment, install the runtime and test packages:

```bash
python -m pip install pandas pytest
```

Run the pipeline with its default paths:

```bash
python pipeline.py
```

The default input is `sales.csv` and the default output is `revenue_by_region.csv`. Explicit paths are supported in either form:

```bash
python pipeline.py --input sales.csv --output revenue_by_region.csv
python pipeline.py sales.csv revenue_by_region.csv
```

Run all employer and project tests with:

```bash
python -m pytest
```

## Expression behavior

`add_virtual_column` accepts existing column names, parentheses, and binary `+`, `-`, and `*`. It uses a restricted syntax-tree interpreter rather than `eval` or `exec`. Labels may contain only ASCII letters and underscores. Malformed syntax, unsupported operations, unknown columns, invalid labels, and failed calculations produce an empty DataFrame. A successful call returns a copy and does not mutate its input.

## Source findings and handling

The CSV has 1,507 data rows: 1,505 transaction rows, one repeated header, and one `TOTAL` control row.

| Finding | Affected rows | Handling |
|---|---:|---|
| Repeated header in the data | 1 | Identify and remove it after locating the controls. |
| `TOTAL` summary/control row | 1 | Reconcile it, then exclude it from transactions. |
| Exact duplicate extras | 5 | Verify raw controls first, then keep the first exact row and remove the extras. |
| Missing unit price | 4 | Fill only when that product has exactly one observed nonmissing price; otherwise fail. |
| Blank discount | 963 | Convert to exactly zero, as the source definition says blank means no discount. |
| Negative quantity | 6 | Retain as returns so they reduce revenue. |
| Noncanonical region text | 15 | Strip surrounding whitespace and apply title case, then validate against the five known regions. |
| Comma decimal unit price | 7 | Accept either comma or dot as the decimal separator. |
| Spaces inside quantity | 4 | Remove spaces before strict integer conversion. |

Before any duplicate is removed, the pipeline sums all raw transaction quantities and discounts. It requires those values to equal the supplied controls: quantity `37150` and discount `65924.67`. Numeric money calculations use `Decimal`; output totals are formatted to two decimal places. Empty or malformed required values, unknown regions, invalid dates, nonpositive prices, negative discounts, conflicting order IDs, and ambiguous price recovery fail closed.

## Assumptions

- Exact duplicate records are export artifacts. This is not proven by the data, so only fully identical rows are removed and only after raw reconciliation.
- Negative quantities represent returns; their supplied discounts retain their original sign in the formula.
- A product's unique observed price is suitable for its missing historical prices. The pipeline refuses imputation if observed prices disagree.
- The authoritative region vocabulary is `Central`, `East`, `North`, `South`, and `West`.
- Revenue is calculated for each cleaned line as `quantity * unit_price - discount`, then summed by region in the stable order above.
