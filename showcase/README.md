# CloudFide · Agentic Data Engineering / real implementation case study

This is the **Polish/English public explanation** of a real recruitment engineering delivery, not a simulated AI dashboard. Its job is to help an engineering reviewer understand **what the assignment required, what was implemented, how Microsoft Foundry was actually used, what each agent concluded, and what the deterministic code produced**.

## The actual system

- `solution.py` implements the requested virtual-column function with constrained expression validation.
- `pipeline.py` turns the raw sales export into five net revenue totals using an approved Pydantic policy, Decimal arithmetic, reconciliation and independent tests.
- `agentic/run.py` runs three **read-only reviewers** with Microsoft Agent Framework, sequentially using `SequentialBuilder` and `FoundryChatClient` on the `gpt-5.6-sol` deployment.
- GitHub Actions authenticates to Azure using an OIDC federation. The report and its integrity checks are tied to a concrete commit.
- The currently recorded run is [#44331275568](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44331275568): **3 validated reports, 16 measured tool invocations and 90.8 seconds**. **79 deterministic tests** passed on Windows and Ubuntu in related CI. The computed net revenue is **2,570,247.03**.
- Three real code corrections arose from the wider human-directed AI review process: [PR #1](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/1), [PR #2](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/2) and [PR #3](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/3).

## Evidence contract

Public files:
- `data/evidence.json` — source and output hashes, reconciliation results, test counts, reviewed commit and allowed tools.
- `data/agent_trace.json` — actual time-stamped, privacy-safe tool events, no fabricated spans or per-agent attribution.
- `data/foundry_reports.json` — the **verbatim original English summaries** and a small selection of verbatim finding statements from the recorded Foundry report. Editorial explanations shown in Polish and English are explicitly separate from those original outputs.

The [original Foundry JSON artifact](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44331275568) is the primary source. Download access to workflow artifacts may expire under the workflow's retention policy. No raw model prompts, tool arguments, secrets, protected Azure endpoints or unpublished task instructions are embedded in this showcase.

**Scope limits:** no autonomous Engineer edits or PR creation; no GitHub MCP inside reviewer workflows; no verified Application Insights exporter or per-agent token/cost telemetry; no measured agent-detection benchmark. The Fault-Injection Lab measures deterministic test-gate sensitivity, not model accuracy.

## Local preview

```bash
cd showcase
node server.mjs
```

Open `http://localhost:4173/?lang=pl` or `http://localhost:4173/?lang=en`. No build step, external framework, API key or database is required.

## Quality gates

`node --test showcase/server.test.mjs` verifies HTTP behavior and content-security headers. `python -m pytest tests/test_showcase_evidence.py` compares published figures with committed source, result and report hashes. GitHub Actions additionally checks JavaScript syntax and takes Polish/English Chromium screenshots on desktop and mobile.

Railway serves only the `showcase/` directory, independently of the ETL and Foundry project.
