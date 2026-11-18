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


## Two-part portal (November 18 integration)

The public site is now split into two deliberately distinct experiences:

- **Results:** `/index.html?lang=pl` or `?lang=en` — recruitment task, inputs, five-region outcome, validation and pull-request evidence. The homepage contains the actual responsibility chain **human decision-maker → ChatGPT architect/implementer → GitHub CI + Foundry three-role review → independent test gate**. This is a documented collaboration, **not** a claim that ChatGPT was a fourth running Foundry agent.
- **Engineering Lab:** `/engineering.html?lang=pl` or `?lang=en` — original Foundry reviewer summaries, 16 measured tool calls, role-scoped capabilities, schema/decision code, OIDC runner connection and optional protected real execution.

The recorded panel never invents model outputs or times. The live section requests the **existing GitHub Actions** review rather than starting a cloud model inside the browser.

### Provision protected recruiter executions

By default **live launch is disabled**. This is intentional: the portal contains no embedded GitHub PAT or Azure token.

Set these **Railway service environment variables**, as confidential/sealed values:

- `GITHUB_WORKFLOW_TOKEN`: a *fine-grained GitHub token scoped only to this repository*, granting **Actions: Read and write** to dispatch exactly `.github/workflows/agent-review.yml` and read the run status. Avoid classic wide-scope `repo` tokens. Use a short expiration and rotate after the interview.
- `REVIEWER_ACCESS_CODE`: separate randomly generated high-entropy passcode of 20+ characters; share it privately with the recruiter. This code is checked server-side and **never sent to GitHub or Azure**.
- `PUBLIC_BASE_URL`: `https://engineering-intelligence-production-a972180f.up.railway.app`, only if using a different deployment hostname (the default is already set).

After provisioning, `GET /api/live/capabilities` returns `liveReady: true`. The real workflow uses **Azure OIDC on main** with a read-only GitHub MCP tool and separate metadata-only event JWTs signed by GitHub OIDC. The portal verifies the exact branch, workflow reference, repo, run and expected audience; it never accepts unauthenticated simulated tool traces. Only 2 launches/day, 1 concurrently active and a 30-minute cool-down are permitted. The in-memory demo session store is **single-replica and restart-volatile**; do not use this gateway as a durable, multi-node billing or authorization system.

**Reviewer UX:** open Engineering Lab → enter code → start → see real GitHub job steps, actual tool completion metadata and Pydantic-validated agent report summaries. The original GitHub run link is available for independent auditing. The workflow isn't classified as successful until its existing source hashes and Pydantic reviews pass.

### Data and code security boundaries

- ETL never needs Foundry to compute revenue. Pandera validates the real Decimal transaction DataFrame without coercion.
- Model `decision_proposals` are strictly schema-checked and written to an atomic ledger. They always remain `pending_human_review`. On successful workflow completion, a separate GitHub job with write-only audit-branch access persists the ledger on `foundry-evidence-ledger`, not `main`.
- The **read-only** GitHub MCP server is instantiated by the real Engineer reviewer using the scoped GitHub Actions token, pinned to `ghcr.io/github/github-mcp-server:v2.1.0`. The reviewer cannot write to the repository.
- The **autonomous regression code author** is intentionally a separate **manual** workflow, `agent-coding-proposal.yml`. A Foundry agent writes a new, strictly allowlisted Python test proposal. A separate job without Azure or write-scoped credentials validates and executes it. Only after tests pass does another job open a **draft PR**; humans remain responsible for review and merge. The reviewer portal does not expose this privileged coding workflow to anonymous visitors.
- Source content, model prompts, full tool parameters, Azure credentials and private environment variables are excluded from public event payloads and static responses.
- In-process per-agent wall-clock middleware and SDK-provided usage counters are recorded where available. **Costs are not invented.** Active Azure Application Insights export requires the existing protected `APPLICATIONINSIGHTS_CONNECTION_STRING` secret to be provisioned in the GitHub Actions environment; the recorded legacy run has no exported trace ID.
