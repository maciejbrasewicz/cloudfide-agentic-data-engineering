# Evidence-driven agentic engineering for a deterministic ETL

This is **one recruitment task** with two complementary execution paths, rather than a separate product.

```text
source task (outside repo) + sales.csv + supplied tests
               |
               v
[Data Architect Agent] — read-only profiling tools, approved policy
               |
               v
[Data Engineer Agent] — read-only code/test inspection, bounded pytest
               |
               v
[Verification Engineer Agent] — independently challenges evidence and results
               |
       Pydantic reports (UNTRUSTED)
               |                    .-----------------------------.
         human review / tests        | CI on every push and PR    |
               |                    |                             |
               v                    v                             |
  versioned data policy        deterministic pandas ETL           |
               |                    |                             |
               +--------------------+----> revenue_by_region.csv  |
                                    |                             |
                                    +----> data_quality.json -----'
```

## Why each boundary exists

- **LLM / source data:** tools return measured data and sampled records. The model's interpretations are hypotheses, not facts. Raw transaction data is untrusted instructions; no tools permit running code found in a cell.
- **LLM / policy:** `DataPolicy` has a fixed version and `Literal` strategies; extra keys and executable snippets are rejected. Agents can recommend changes but cannot silently deploy a new policy.
- **LLM / code:** distinct read-only tool sets; no arbitrary command tool. The only execution tool calls a fixed pytest command with a timeout. No agent can modify production code or tests during evaluation.
- **Source / ETL:** source control is checked *before* deduplication. `TOTAL` is not an order. Missing prices are inferred only with unique reference values.
- **ETL / CI:** a deterministic independent check validates region totals and commits; the agent review is not a gate, so Azure outages cannot stop a valid ETL solution.

## Configuration and run modes

| Mode | Dependencies | Purpose |
|---|---|---|
| `python pipeline.py` | pandas, pydantic | Normal deterministic task result |
| `python -m pytest` | quality extras | Independently validate ETL, parser, assumptions |
| `python -m agentic.run` | Foundry extras + Azure identity | Explicit three-agent audit of this same solution |

The agent workflow uses the documented `FoundryChatClient` with a project-scoped endpoint and `SequentialBuilder` from Microsoft Agent Framework. Each participant sees previous context, but its available tools differ. The workflow is bounded to three agent passes and returns structured JSON, parsed against Pydantic models. It never auto-merges or publishes changes. Optional telemetry uses Microsoft OpenTelemetry with prompt-content capture disabled.

## Trust and reproducibility constraints

1. Strict allowlist of local files readable by agents.
2. No arbitrary shell-execution or file-edit tool exposed to any agent.
3. Raw input and output file hashes embedded in quality report; agent report also records contract SHA-256.
4. Original assignment instructions never committed.
5. Azure authentication via Entra ID (`az login` locally or GitHub OIDC); no secret in source control.
6. Versions of framework components are pinned, and a resolved `uv.lock` is committed and CI uses `uv sync --locked`.

## Execution evidence (18 November 2026)

- **Data Engineering:** GitHub Actions runs Ruff, supplied tests, property tests, integration tests, source-control reconciliation and byte-for-byte regenerated artifact comparison on Windows and Ubuntu. The task itself requires no Azure connection.
- **Identity:** GitHub Actions successfully exchanged a branch-scoped immutable OIDC token for a Microsoft Entra identity with project-scoped Foundry access. No stored client secret.
- **Agentic review:** [successful evidence-bound Foundry run](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44314174941) returned all three validated reports using `gpt-5.6-sol`; source, policy, test, code, dependency and output hashes were attested.
- **Feedback loop:** The first independent agent review exposed normalized-before-deduplication duplicates, weak strict-region enforcement and unvalidated control-row structure. All were fixed through [PR #1](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/1). [PR #2](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/2) removed unauthorized blanket trimming and extended an independent `csv` + `Decimal` oracle to the original `TOTAL` record. [PR #3](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/3) added artifact-path collision protection before writes and source/policy provenance hashing before generating output. Each change passed Windows and Ubuntu CI prior to merge.
- **Limitations:** The Architect's narrower source tools cannot independently prove all pipeline properties; model findings remain suggestions, not facts. Application Insights exporter configuration is optional and not represented as active until verified. No autonomous code execution or auto-merge by LLM is permitted.

The project illustrates controlled use of probabilistic reasoning inside a deterministic software delivery process, not an LLM-dependent financial calculator.
