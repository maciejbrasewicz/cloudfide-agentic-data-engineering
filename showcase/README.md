# Engineering Intelligence / Field Report 001

A standalone, **dependency-free static web experience** showing the real delivery and verification history of the CloudFide agentic Data Engineering task.

## Purpose

A technical reviewer should be able to explore the system architecture, role-scoped tool access, three real code-correction cases, the raw-to-clean data lifecycle, the independent verification and the source-linked evidence without reading raw Python files first.

## Source of truth

- `data/evidence.json` is a **curated, recorded snapshot**, grounded in a successful [Foundry review run](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44318354937) and the [CI result](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44318536294).
- The snapshot is explicitly **not live monitoring** and has no fabricated trace IDs, spans, token usage, costs or completion times. See `observability.traceStatus`.
- The three engineering cases refer to real merged PRs [#1](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/1), [#2](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/2) and [#3](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/3). Humans directed those repairs; agents in the present repo are read-only reviewers.
- Business assumptions about removing duplicates, reconstructing prices and interpreting negative quantities remain unproven by test results alone.
- The assignment instructions themselves never appear in this app or the repository.

## Run locally

From `showcase/`:

```bash
python -m http.server 4173
```

Open http://localhost:4173.

The app is plain HTML/CSS/JS. Navigation, architecture nodes, cases, agent details, revenue exploration, decision expansion and hash copying work in a browser without any API keys or paid backend.

## Deploy

Link this repository to a static hosting project whose root directory is `showcase`. Vercel uses the included `vercel.json` security headers; there is no build step.

## Engineering boundary

The UI renders curated evidence, never interprets untrusted model output as HTML. The JS escaping helpers prevent textual evidence from becoming executable markup; external links are constrained to GitHub. Snapshot integrity tests in `tests/test_showcase_evidence.py` ensure numerical fields and displayed source hashes agree with committed ETL artifacts.

**Future instrumentation:** connect OpenTelemetry from GitHub runners to Foundry/Application Insights, export redacted trace summaries with measured durations and model usage, and add a deterministic fault-injection evaluation. Until those real measurements exist, the UI keeps their status visibly unconfigured.
