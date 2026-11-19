# Virtual columns & auditable sales pipeline

**A complete Data Engineering assignment and a verified three-agent software delivery workflow.** The deterministic Python baseline solves virtual-column arithmetic and sales ETL. Independently, three REAL Microsoft Foundry roles design a task contract, **write new source files**, run independent checks, repair actual failures, and open a SHA-verified draft pull request for human review. The LLM is never used for financial calculations.

**Two deliberately different layers — one project, one portal:** `solution.py` and `pipeline.py` at repo root are the stable, audited reference baseline used by the engineering platform; `deliveries/run-<ID>/` in an agent-created draft PR is a **standalone executable deliverable** authored by the real agents. Replacing the running platform with a standalone newly authored pipeline would corrupt its test/verification imports. Results are therefore reviewed and executed in isolation, not auto-merged.

[**Open the unified recruiter showcase**](https://engineering-intelligence-production-a972180f.up.railway.app/?lang=pl#execution) · [**Latest full 3-agent run #44485096373**](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44485096373) · [**Automatically published draft PR #35**](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/35) · [**Exact-SHA independent CI**](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44487613707)

## Run the right thing

| You want to... | Run / open |
|---|---|
| Run the stable deterministic ETL baseline | `uv sync --locked --extra quality && uv run --no-sync python pipeline.py` |
| Execute the baseline's complete test suite | `uv run --no-sync python -m pytest` |
| **Run the actual agent-generated candidate** | `uv run --no-sync python scripts/replay_delivery.py --run-id 44485096373 --commit 73ab197159f8ed5a595bdd99a88b01707371d12e --base 737baf62ad7fb17f89a194a4dcb904bf0081ceea` |
| Inspect the candidate and the third agent's pytest | [Draft PR #35](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/35) → `deliveries/run-44485096373/` |
| Observe or **start** a new complete agent delivery | [GitHub Actions — CloudFide delivery](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/workflows/engineer-e2e.yml) → Run workflow → `rebuild` / 3 rounds / draft |
| Inspect without a GitHub login and verify the actual CSV now | [Live recruiter portal](https://engineering-intelligence-production-a972180f.up.railway.app/?lang=pl#execution) → agent history + independent recalculation |

The candidate replay requires **Docker** and uses the identical SHA-admission gate, no-network nonroot Docker runtime and separate `decimal.Decimal` oracle as the GitHub candidate CI. It does **not** execute generated Python on your host. For an audit trail use `--evidence-dir ./reviewer-evidence`. The full agent execution is separate, incurs Foundry model usage, and is limited to authenticated operators.

See [**reviewer operation and architecture**](docs/reviewer-architecture-and-operation.md) for proof boundaries, required permissions, and security controls.

## Quick start

Requires Python 3.11+.

```bash
uv sync --locked --extra quality
uv run --no-sync python pipeline.py
uv run --no-sync python -m pytest
```

Without uv: install pandas, pydantic, pytest and hypothesis in a virtual environment, then run `python pipeline.py` and `python -m pytest`. The repo includes the original `sales.csv` and `test_virtual_column.py` unchanged.

Output: `revenue_by_region.csv`. Audit: `reports/data_quality.json`.

## Verified result

| Region | Revenue |
|---|---:|
| Central | 515824.67 |
| East | 442219.91 |
| North | 665897.52 |
| South | 504036.04 |
| West | 442268.89 |
| **Total** | **2570247.03** |

Amounts are calculated using `decimal.Decimal`, not floating point. The final CSV is stable and sorted alphabetically by region.

## Source issues, counts, and decisions

Counts are from the **supplied** 1507-row CSV. Two rows are not order lines: one repeated header and one `TOTAL` control record. That leaves 1505 raw order lines, including five exact duplicates. The cleaned dataset contains **1500** order lines.

| Observation | Affected raw rows | Handling / rationale |
|---|---:|---|
| Repeated header embedded within data | 1 | Exclude from transactions |
| `TOTAL` summary row | 1 | Validate raw quantities and discounts against this row **before** deduplication, then exclude |
| Exact duplicate order lines | 5 additional rows | Keep one copy; do not dedupe on order ID alone |
| Noncanonical region casing / whitespace | 15 | Strip spaces and normalize to known five region labels |
| Prices written using decimal comma | 7 | Parse both `,` and `.` as decimal separators |
| Quantities with grouped thousands | 4 | Remove embedded group spaces before integer parsing |
| Missing unit price | 4 | Infer from product **only when all known normalized prices for that product agree**; otherwise fail |
| Negative quantities | 6 | Keep as returns; net revenue may be negative |
| Empty discounts | 963 | Interpret as 0 per task; **959 remain after deduplication** |
| High-quantity orders | 4 | Retain because format is valid and source totals reconcile; no arbitrary clipping |

A row can belong to multiple categories. **Metric stages matter:** source rows, repeated headers, region formatting and original blank-discount counts are measured on the incoming export; recovered prices, discount zeros, and retained negative quantities are measured after source-exact deduplication. Totals and deduplication are **not** interchangeable: the `TOTAL` row reconciles with the raw 1505 transactions including duplicates, not the 1500 cleaned rows.

### Explicit assumptions

1. Identical duplicate rows are repeated export lines rather than distinct genuine sales. This is not provable from the export alone; the decision is documented and testable.
2. Negative quantity means a return or credit, so it is retained. Discounts are applied per line as specified.
3. For a missing unit price, same-product prices are used **only if the reference value is unique**; otherwise processing stops with `DataQualityError`. It is an assumption, not a claim of real historical pricing semantics.
4. Unexpected region names, dates, malformed financial values, inconsistent source `TOTAL`, ambiguous prices, and unsupported policies are treated as unrecoverable rather than guessed.
5. All monetary amounts use two decimal places; the supported CSV price and discount precision is cents.
6. The virtual-column function accepts only ASCII letters and underscores as labels, with no numeric suffix. Its expression supports referenced columns and `+`, `-`, `*`, unary signs and parentheses; numeric literals, function calls and new-column overwrites are not permitted. Invalid inputs return an empty DataFrame. The misleading `price_total` heading in the provided example is treated as a typo: the supplied `new_column` is respected.

## Independent quality controls

- Source checks: counts and raw `TOTAL` for quantity and discount before deduplication.
- Output checks: no silent row loss; exact region membership; line revenue sum equals grouped sum.
- Tests: original tests, additional edge/immutability/security tests, independent decimal calculations, negative tests that verify fail-closed behavior, and Hypothesis property tests.
- Reproducibility: CI reruns the pipeline and verifies that its output and audit exactly match the committed artifacts.

The checks do not simply compare the program against its own calculated output: several tests use **independent arithmetic** and fixed expected regional totals.

## Autonomous Foundry delivery — actual execution, not a read-only review

The original task instructions remain outside the repo and enter trusted GitHub Actions only via `CLOUDFIDE_TASK_SPEC_B64`. GitHub Actions signs into Microsoft Foundry using Azure OIDC restricted to the trusted `main` branch; no Azure credentials are present in generated-code sandboxes or in Railway.

1. **Data Architect** reads the original specification, employer tests, CSV and approved data policy. A deterministic gate verifies source facts and policy decisions. New policy proposals halt instead of being self-approved.
2. **Data Engineer** writes real `solution.py`, `pipeline.py`, `tests/test_*.py` and `README.md` into a write-limited workspace; model-produced code is inert until admitted by a trusted checksum gate.
3. **Independent P3** runs candidate Python in a Docker container without network or credentials and verifies the original CSV with a separate `Decimal` oracle.
4. **Bounded retries** pass real failure logs back to the Data Engineer (at most 3 attempts). SHA-linked artifacts and the deterministic P5 controller record accepted/rejected source lineage.
5. **Verification Engineer** independently reads the actual candidate, authors a new executable test, and requests validation. P4 proves it passes on the real candidate and fails against a deliberately broken arithmetic implementation.
6. **P6** publishes exactly the verified files to `deliveries/run-<ID>/` in a **draft PR**, never auto-merges. Separate CI validates the original employer fixtures, source/commit SHA and candidate implementation.

**Latest complete execution:** [run #44485096373](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44485096373) → rejected versions 1 and 2, accepted version 3 → P4 mutation-sensitivity PASS → automatically created [draft PR #35](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/35) → exact-SHA CI PASS. 18/18 candidate tests and independent five-region total **2,570,247.03** (source currency not established).

### Two modes and reviewer permissions

- `rebuild` hides existing reference code from the new Data Engineer: original spec, input CSV, employer tests and approved policy define the task.
- `improve` permits only allowlisted baseline files and independently verified changes, not arbitrary repository writes.

Anyone may inspect evidence and independently recalculate the input in the single public portal. Full paid Foundry execution from that portal requires a Railway-side **fine-grained GitHub Actions token** and a separate **reviewer access code**, limited to two dispatches per 24 hours. Github Actions alone handles PR publishing, Azure secrets remain on trusted workers, and only a human can merge or authorize a policy change.

**Measured vs unimplemented:** executed Foundry + isolated P3/P4 + bounded repair + auto draft PR + exact-SHA CI are proven. Historical read-only review, bounded full delivery and the public result calculation are different modes. Future policy approval and resume features must not be described as proven until their actual execution tests pass.

**Dependency safety:** the pinned Foundry runtime avoids `agent-framework` 1.26.1/1.26.2, reported malicious on 17 Nov 2026; dependencies are installed from locked versions. Use `uv sync --locked` and verify SDK integrity when updating.

## Implementation footprint

The trusted baseline's `solution.py` is a small AST evaluator without `eval()` or `exec()`. The trusted `pipeline.py` is plain pandas with Decimal arithmetic; `contracts/data_policy.json` is allowlisted and versioned. An agent can write separate candidate files but never execute them inside Azure/OIDC jobs. The existing [single recruiter web portal](showcase/) is an evidence and controlled-execution interface, not a second ETL backend; processing 1,500 rows does not require Fabric, Spark, or an LLM. For deploy and OIDC details see [runbook](docs/deployment.md).
