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
| `pytest` | quality extras | Independently validate ETL, parser, assumptions |
| `python -m agentic.run` | Foundry extras + Azure identity | Explicit three-agent audit of this same solution |

The agent workflow uses the documented `FoundryChatClient` with a project-scoped endpoint and `SequentialBuilder` from Microsoft Agent Framework. Each participant sees previous context, but its available tools differ. The workflow is bounded to three agent passes and returns structured JSON, parsed against Pydantic models. It never auto-merges or publishes changes. Optional telemetry uses Microsoft OpenTelemetry with prompt-content capture disabled.

## Trust and reproducibility constraints

1. Strict allowlist of local files readable by agents.
2. No arbitrary shell-execution or file-edit tool exposed to any agent.
3. Raw input and output file hashes embedded in quality report; agent report also records contract SHA-256.
4. Original assignment instructions never committed.
5. Azure authentication via Entra ID (`az login` locally or GitHub OIDC); no secret in source control.
6. Versions of framework components are pinned, and a frozen `uv.lock` must be generated and committed after dependency verification in a network-enabled environment.

## Implementation status

- **Completed and locally verified:** source normalization, independent Decimal reconciliation, published sample totals, original and custom deterministic tests.
- **Prepared, not yet executed against Foundry:** Microsoft Agent Framework workflow, Azure identity and Application Insights integration, GitHub manual agent review job.
- **Awaiting cloud configuration:** actual Foundry project endpoint, model deployment, OIDC federation in target Azure tenant, commit and CI run on a new GitHub repository.
