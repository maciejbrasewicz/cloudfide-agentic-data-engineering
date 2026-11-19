# P6 — SHA-verified draft PR publication and isolated candidate CI

After actual P1 Architect, P2 code authoring, P3 independent financial and
employer tests, at most three evidence-driven P5 attempts, and P4 REAL
Verifier's own executable test including a deliberately broken negative
control, P6 may publish a human-reviewed **draft PR**.

## Strict trust separation

The P6 job does not have Azure OIDC, Foundry model access or the original
assignment secret. It has GitHub contents, pull-request and Actions write
permissions ONLY for publishing the reviewed candidate and triggering
new CI. It never imports/executes generated code. Its deterministic
publisher_validate step independently checks original fixture SHA, actual
P5 selected candidate, P4 independent PASS and mutation-sensitivity evidence,
the actual generated test bytes, and the financial output from the P4
independent sandbox. The original private task text is NOT in the PR.

Only allowlisted paths are copied into the draft:
solution.py, pipeline.py, README.md, own tests/test_*.py,
tests/test_verifier_generated.py, and independently produced
revenue_by_region.csv. It also writes a trusted public provenance receipt to
reports/agentic_delivery_manifest.json. No agent is allowed to change
test_virtual_column.py, sales.csv, contracts/data_policy.json, workflow
definitions or dependencies in this branch.

The PR is created from one fresh commit whose parent is the original
P1-P5 main commit. No auto-merge. Explicit human code, source and business
assumption review remains mandatory.

## Exact-SHA isolated CI

A regular GitHub Actions workflow triggered by an automatic GITHUB_TOKEN
push may not run. P6 therefore explicitly dispatches the protected
candidate-ci.yml workflow on the **trusted main branch**, with:
- published draft branch name and immutable exact SHA,
- original source run id,
- original base SHA.

The CI job checks that the Git branch has NOT moved, the candidate commit
has the exact base as direct parent, all diff paths are allowlisted, all
generated source bytes match the publisher manifest and all original employer
inputs are unchanged. This checkout is trusted main code; it never imports
the candidate on the host.

Candidate code is staged into the static P3 Docker image and run with
no network, no secrets, nonroot, read-only root/candidate mount and limited
resources. Independent csv+Decimal again checks the full regional result.
The job posts a GitHub commit status with context
agentic-delivery/isolated-candidate-ci to the exact published candidate SHA,
and uploads actual logs. A created draft PR is therefore **not assumed to
pass CI**. Green status requires real isolated execution.

## Operator trigger

https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/workflows/engineer-e2e.yml

Branch main, mode rebuild (or improve), max_rounds 1-3,
publish_draft_pr true. Push-triggered deployments use the default true
to create a draft PR ONLY on an actual full P4 PASS. Manual false can
validate without publishing. A failed model, sandbox or verifier cannot
enter the publishing job.

P7 will later surface the actual latest run/branch/PR evidence in the single
existing engineering showcase. The existing public data-engineering baseline
remains untouched by autonomous candidate failures.
