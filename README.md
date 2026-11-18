# Virtual columns & auditable sales pipeline

A small, deterministic **pandas** solution to the virtual-column recruitment task. It reads the supplied sales export, verifies its original control totals, repairs documented data defects, computes line revenue using the required `add_virtual_column` function, and writes aggregated revenue by region. The optional Microsoft Foundry workflow reviews **this same solution**; no cloud service is required to run the task.

## Quick start

Requires Python 3.11+.

```bash
uv sync --extra quality
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

A row can belong to multiple categories. Totals and deduplication are **not** interchangeable: the `TOTAL` row reconciles with the raw 1505 transactions including duplicates, not the 1500 cleaned rows.

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

## Optional agentic engineering workflow

This repository also contains a *read-only*, three-role Microsoft Foundry review of this same deliverable: **Data Architect → Data Engineer → Verification Engineer**. It is not a second application and is not called by the production ETL. Agents have narrow function tools to inspect source data, inspect named files, check the approved contract, run tests, and read reconciliation evidence. Their findings are structured with Pydantic and remain **untrusted suggestions** until reviewed against executable tests. A separate `agentic.verify` provenance gate checks the report against the exact source, policy, code, test-suite and output hashes. See [architecture](docs/architecture.md).

```bash
uv sync --extra quality --extra foundry
az login
cp .env.example .env  # set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL
uv run --no-sync python -m agentic.run --task-file /path/outside/repo/taskvirtualcolumn.md
```

The original task instructions must stay **outside** this repository. Only the instructions are passed at runtime to the agent. The emitted `agentic_review_runtime.json` is intentionally untracked: it may contain generated text, and it must not be represented as a validated result before real execution.

After a successful local agent run, validate evidence with `uv run --no-sync python -m agentic.verify --input agentic_review_runtime.json`. Re-run the agents after code, data, policy or tests change; stale reports deliberately fail verification.

GitHub Actions has separate workflows: `ci.yml` (no Azure secrets or model calls) and `agent-review.yml` (manual trigger, Azure OIDC, read-only tokens and short artifact retention). Set GitHub repository variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`. The Azure identity must have least-privilege access to the Foundry project and an OIDC federated credential scoped to this repository's workflow.

**Security note, 18 Nov 2026:** Versions `agent-framework` 1.26.1 and 1.26.2 were reported as malicious on PyPI on 17 Nov. This project does **not** directly depend on the `agent-framework` metapackage and explicitly pins `agent-framework-core==1.26.0` and audited component versions. Before installing Foundry extras in an Azure-authenticated environment, verify resolved dependencies and generate/commit `uv.lock` in a network-enabled, clean environment. CI currently resolves dependencies using declared constraints; commit a reviewed `uv.lock` for reproducible dependency resolution before final submission.

## Implementation footprint

`solution.py` is a small AST evaluator without `eval()` or `exec()`. `pipeline.py` is plain pandas with Decimal arithmetic. `contracts/data_policy.json` is an allowlisted, versioned policy that controls supported repair decisions during execution; the LLM never supplies code or arbitrary values to execute. There is no Fabric workspace, Spark cluster, web dashboard, or runtime AI dependency for processing 1500 rows. For the concrete Windows/GitHub/OIDC rollout, see [deployment runbook](docs/deployment.md).
