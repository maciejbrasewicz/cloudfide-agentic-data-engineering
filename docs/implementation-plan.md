# CloudFide — implementation status and delivery plan

## Current system: implemented and verified

The recruitment solution is complete: `solution.py`, `pipeline.py`, `revenue_by_region.csv`, original fixtures, regression/property tests, approved `DataPolicy`, independent `csv + Decimal` checks and cross-platform CI.

The present `.github/workflows/agent-review.yml` is a **real, read-only, three-agent Foundry audit** of that solution; it is **not** an autonomous code-delivery workflow. A verified run is [44379368776](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44379368776). `agent-coding-proposal.yml` is limited to proposing a single additional regression test, and its full execution has not yet been verified.

The consolidated bilingual engineering showcase is hosted separately but remains one portal.

## Target: incremental implementation (not yet complete)

**P0:** committed and tested (private task intake, input hashes, fixture integrity).

**P1:** implemented in source and tested on Windows, Linux and the pinned Agent Framework SDK: real Data Architect tools, independent original CSV profiling, typed evidence contract and fail-closed policy gate. A *live P1 Foundry execution on the private original specification is not yet verified*; it requires the operator to set the Actions secret `CLOUDFIDE_TASK_SPEC_B64` and run `architect-e2e.yml`. See [P1 operator guide](architect-operator.md). No code-generation claim is made for P1.

**P2–P7:** not implemented yet. The existing auditor remains available separately.


Read [Autonomous Data Engineering Delivery — architecture, milestones, test gates and E2E acceptance](autonomous-delivery-plan.md).

The target system must take the **original assignment specification provided privately at runtime**, original `sales.csv` and supplied tests, then run:

1. **Data Architect** — actual input profiling and evidence-linked policy/contract proposal.
2. **Data Engineer** — actual code, tests, README and candidate patch creation in a restricted workspace.
3. **Independent sandbox** — run the candidate without Azure credentials or write permissions.
4. **Verification Engineer** — code inspection and at least one executable independent counterexample.
5. **Deterministic controller** — accept, request bounded rework or stop with a supported reason; never trust a model-only success statement.
6. **Draft PR** — submit validated code and evidence for human review; never auto-merge.

This replaces the earlier aspirational gates in this document, several of which were written before the now-successful Foundry and CI deployments. The existing audited solution must remain intact until the new pipeline passes the plan's ten end-to-end acceptance scenarios.
