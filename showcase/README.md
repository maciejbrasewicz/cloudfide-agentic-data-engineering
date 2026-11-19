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

**Scope and verification:** The recorded run #44331275568 contains original Foundry reports and measured tool calls; it does not include verified Application Insights spans, provider token usage, per-agent runtimes or verified pricing. The later implementation adds Pandera validation, a human-gated DataDecision ledger, scoped GitHub MCP review, per-agent runtime instrumentation, and a protected execution API. Features requiring additional deployment credentials or independent runtime evidence remain explicitly identified as such.

## Local preview

```bash
cd showcase
node server.mjs
```

Open `http://localhost:4173/?lang=pl` or `http://localhost:4173/?lang=en`. The Results, Multi-Agent Review, System Specification and Execution Control sections coexist on the same page. No build step, external framework, API key or database is required.

## Quality gates

`node --test showcase/server.test.mjs` verifies HTTP behavior and content-security headers. `python -m pytest tests/test_showcase_evidence.py` compares published figures with committed source, result and report hashes. GitHub Actions additionally checks JavaScript syntax and takes Polish/English Chromium screenshots on desktop and mobile.

Railway serves only the `showcase/` directory, independently of the ETL and Foundry project.


## Unified case study and execution interface

The public interface is one responsive, bilingual technical report at `/?lang=pl` or `/?lang=en`, with an uninterrupted hierarchy:

1. The task and deterministic deliverables.
2. Computation vs agent review architecture and exact source evidence.
3. Original Foundry reviews and measured tool events.
4. Sales results and engineering changes arising from review.
5. Integrated system specification and controlled workflow execution.
6. Operational verification status and direct evidence links.

There is **no independent dashboard or second portal**. Existing `/engineering.html` bookmarks permanently route visitors to the `#technical` section of this same page. It uses professional component labels: **DataPolicy, Engineering Pipeline, Agent Orchestration, DataDecision, Assurance and Execution Control**.

### Optional authenticated recruiter execution

The real execution UI is directly below the global header. It becomes available when Railway provisions the two private credentials; public evidence inspection never requires a reviewer code. The portal keeps original Foundry evidence available regardless. To enable the protected `workflow_dispatch` path, set Railway service variables:

- `GITHUB_WORKFLOW_TOKEN`: repository-scoped, short-lived fine-grained GitHub token allowing Actions read/write (dispatch plus run polling). Do not use a general account-level token.
- `REVIEWER_ACCESS_CODE`: independent, high-entropy access code of at least 24 characters, distributed privately to an intended reviewer.
- `PUBLIC_BASE_URL`: only if the public hostname changes; used to bind event OIDC audience.

The browser posts only an access code to the backend, which permits at most five launches per rolling 24 hours, a single active workflow and a short cooldown. Actions runners authenticate event delivery with short-lived GitHub OIDC. Server verifies the expected workflow, repository, ref, run ID, JWT signature and publisher audience. Only allowlisted event metadata and explicitly untrusted report summaries can reach the browser. **No Azure key, arbitrary shell command, prompts or raw tool arguments are exposed.**

The Railway in-memory session store is single-replica and restart-volatile; it is not described as a durable task queue. For live readiness inspect `GET /api/live/capabilities`. A missing token produces `recorded_only`, not simulated execution.

### Engineering controls

- `dataframe_contracts.py`: non-coercive Pandera validation of cleaned Decimal source data before aggregation.
- `agentic/run.py`: actual Microsoft Agent Framework `SequentialBuilder` execution with three independent role-specific reviewers.
- `agentic/github_mcp.py`: official GitHub MCP integration, read-only GitHub Actions token, no repository write permissions.
- `agentic/decision_ledger.py`: evidence-bound unapproved model suggestions with explicit human approval boundary, atomic serialization and separate audit history.
- `agentic/review_metrics.py`: per-agent measured durations; model token usage only when the SDK actually supplies it; absent billing rates produce no cost claim.
- `.github/workflows/agent-coding-proposal.yml`: a separate privileged workflow in which an authoring agent proposes one regression test, isolated no-secret CI executes it, and a distinct job may create a **draft PR**. No autonomous merge.

The latest review controls require authentic cloud execution for operational verification. The static interface does not imply a new agent run was successful when only CI source checks passed.

### Quality gates

`node --test showcase/server.test.mjs showcase/live_gateway.test.mjs` validates the real gateway, strict allowlist, signed OIDC acceptance and unauthorized-event rejection. `pytest tests/test_showcase_evidence.py` enforces original run consistency, bilingual rendering invariants and a unified layout. Chromium screenshots in `.github/workflows/showcase-ci.yml` cover Polish/English desktop/mobile and the embedded technical section.

### Recruiter-first entry and delivery process

The top section now explains exactly what the reviewer launches: a new restricted Foundry Data Architect run, real Data Engineer source authoring with up to three sandbox-gated corrections, a distinct Verification Engineer falsification test, independently executed P4, and publication as a draft PR for human review with separate exact-SHA CI. A second, compact hero diagram separates **technology stack** (Foundry, Agent Framework, GitHub Actions, Azure OIDC, Python, Docker, pytest, SHA-256) from **six delivery stages** (approved specification, Architect, Engineer, P3/P5, Verifier/P4, draft PR/CI). The Architect does not dynamically create agents; GitHub Actions hosts the deterministic orchestration, and human approval is required for business-rule changes and final PR merging.
