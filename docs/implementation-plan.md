# Architecture and implementation plan

## Scope and acceptance gates

**Gate 1 — Required task (implemented / locally verified)**

- Preserve the two original test/data inputs, without committing the assignment instructions.
- Safe virtual-column parser in `solution.py`, returning a new DataFrame or an empty one for invalid roles/labels.
- Deterministic `pipeline.py` computes `quantity * unit_price - discount` and writes `revenue_by_region.csv`.
- `contracts/data_policy.json` constrains accepted business rules, and `reports/data_quality.json` records actual metrics.
- Original tests, extra edge-case and integration tests, and a second independent Decimal calculation.
- Acceptance: exact 1500 clean transactions and regional net revenue of 2,570,247.03.

**Gate 2 — Engineering verification (prepared; remote CI not yet run)**

- `ci.yml` performs lint, unit/integration/property tests, pipeline rerun, and Git diff of committed result.
- Generate and commit `uv.lock` in a clean network-enabled machine, verify all resolved dependency versions and their provenance.
- Activate branch protection for CI on the GitHub repository.
- Acceptance: successful GitHub Actions build from a fresh checkout.

**Gate 3 — Agentic audit (code prepared; cloud run awaiting credentials)**

- Establish Foundry project endpoint and model deployment; use Azure CLI credentials locally.
- Authenticate GitHub Actions with Entra workload identity/OIDC, scoped to this repository and manual workflow.
- Three actual Agent Framework participants with separated read-only tools: Architect, Engineer, Verifier.
- Review report must validate against Pydantic schema and show evidence, not free-form model endorsement.
- Acceptance: one genuine Foundry trace, verified tool calls, three parsed agent reports and one resulting tested change/decision, if the agents find a justified issue.

**Gate 4 — Submission (pending GitHub repo)**

- Create a new standalone GitHub repository, not in the Registry9 application repositories.
- Push code and check a clean CI pass; verify all mandatory file names and `revenue_by_region.csv`.
- Put repo URL into the CloudFide form. Public access avoids collaborator setup; if private, add `cf-recruitment` and send the requested email.

## Non-goals

No Fabric workspace, no Spark cluster, no arbitrary LLM-driven data transformations, no hosted web frontend, and no API key in repo. Model outputs cannot mutate approved policies or merge code without review.
