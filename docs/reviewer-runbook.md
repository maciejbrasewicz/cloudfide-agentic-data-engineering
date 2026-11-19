# CloudFide | Reviewer runbook and evidence contract

## What this submission demonstrates

**The assignment is a deterministic Data Engineering solution.** Its financial
calculation uses Python/pandas/Decimal, not AI. The accompanying engineering
system demonstrates that three real Microsoft Foundry roles can analyze the
original assignment, write actual Python code, reject failures, repair the
implementation, author an independent test, and publish only verified source
as a draft PR. **A model cannot authorize its own result.**

There is **one portal**: [CloudFide — live reviewer view](https://engineering-intelligence-production-a972180f.up.railway.app/?lang=en#execution).

The **trusted root implementation** is the stable reference baseline and
platform machinery. The **generated deliverable** is under
deliveries/run-44485096373/ in [draft PR #35](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/35).
Do not silently replace the platform with generated standalone scripts.

## Fastest independent review (no credentials)

1. In the portal, open **Execution**. Click through Architect, three Engineer
   iterations, Verification Engineer and draft-PR publication. Source-code
   excerpts are from actually authored files. Every claimed measured PASS/FAIL
   is associated with a real GitHub Actions or SHA-verified artifact.
2. Click **Recalculate and verify**: a separate Node/BigInt oracle retrieves
   pinned original CSV and candidate output by immutable commit SHA, checks
   source and output hashes, reconciles raw control totals, deduplicates only
   exact source rows, and compares five regional amounts. It is a **fresh**
   calculation, not an agent reenactment or a Python rerun.
3. The live system block shows actual GitHub job states, **the matching
   draft PR** and the exact-SHA independent CI status. A green job alone never
   claims that its downstream CI has passed.
4. Open [full autonomous run #44485096373](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44485096373).
   Its P5 history contains **failed, failed, passed**; P4 independently passed
   on the candidate and rejected a deliberately broken implementation.
5. Inspect [PR #35](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/35)
   and [independent candidate CI #44487613707](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44487613707).
   Candidate commit SHA: 73ab197159f8ed5a595bdd99a88b01707371d12e.
   **Draft remains unmerged and requires human review.**

## Execute the generated candidate safely (Docker required)

From the **repository root** (NOT the standalone candidate folder):

1. Install Python 3.11+ and Docker Desktop/Linux Docker Engine.
2. Install the pinned dependencies: uv sync --locked --extra quality.
3. Execute:

    uv run --no-sync python scripts/replay_delivery.py \
      --run-id 44485096373 \
      --commit 73ab197159f8ed5a595bdd99a88b01707371d12e \
      --base 737baf62ad7fb17f89a194a4dcb904bf0081ceea \
      --evidence-dir ./reviewer-evidence

This uses the source- and SHA-bound intake check, trusted static Docker
image, nonroot no-network execution and separate Decimal oracle. It produces
tests.log, pipeline.log, verification.json and revenue_by_region.csv.
**Never execute the model-authored candidate directly on the host.**

The default root command uv run --no-sync python pipeline.py runs the
**trusted baseline**, not the newly authored candidate. It is deliberately
different from the replay command above.

## Start all three Foundry roles from one portal

The single portal includes an authorized **full delivery launch** panel below the main product introduction, above the task overview. It explains what a fresh run does, while the technology stack and gated P1–P6 workflow are separate cards below. The panel was previously located under
System. Its backend uses a repository-scoped GitHub token stored **only in
Railway**, never sent to the browser:

- GITHUB_WORKFLOW_TOKEN: fine-grained PAT with this repo only; Actions:
  Read and write; no Contents or Pull requests write access.
- REVIEWER_ACCESS_CODE: a separate randomly generated strong secret (at
  least 32 characters), shared privately with an authorized reviewer.
- GitHub Actions also retains CLOUDFIDE_TASK_SPEC_B64 as a repository secret
  and uses trusted-main OIDC for Microsoft Foundry; neither is deployed to
  Railway.

The backend dispatches exactly engineer-e2e.yml on main in rebuild mode,
at most three Engineer iterations, with a draft-PR publication after P4 PASS.
The portal polls real GitHub jobs, not a fake progress timeline. It limits
launches to five per rolling 24 hours and one concurrent run; treat these as
cost controls, not a complete identity platform.

**Acceptance test for the UI:** use the private review access code to start
one authorized real run from the portal; verify it appears in GitHub as
event=workflow_dispatch, contains the matching review_request_id in the
display title, ends with P3/P4 evidence, creates a draft PR and receives a
matching exact-SHA CI status. A historical push-triggered run does not prove
the portal launcher.

## Checkpoints, policy decisions, telemetry

- **P5 checkpoint:** the independent controller reevaluates the actual
  candidate and P3 artifacts and saves a SHA inventory, original dataset and
  policy hashes, selected iteration, source commit and P5 status. GitHub
  Actions retains artifacts for 30 days. Re-run failed jobs in the GitHub
  UI can reuse successful upstream jobs of the same workflow execution.
  The existing exact-SHA candidate CI can independently replay a published
  result. There is **no claim of arbitrary model-context restoration** from
  an old checkpoint.
- **Policy changes:** a valid Architect proposal that differs from
  contracts/data_policy.json creates a SHA-checked GitHub issue requesting
  review. It does not update the policy or let Engineer proceed. A human
  reviews the underlying business assumptions and separately opens a tested
  policy-change PR; only trusted-main policy in a subsequent run is executable.
  Repository branch rules must enforce human review before merging.
- **Real telemetry:** each role emits a measured monotonic elapsed time and
  actual tool-call count; a no-secret job reads real GitHub Actions job
  start/end times and gathers P3/P4/P5 receipts. Prompts, tool arguments and
  private assignment text are not exported. Model-token usage and pricing
  remain null unless genuinely captured; total job duration is not presented
  as model-only latency.

## Objective acceptance

The original raw export contains 1,507 rows: an embedded header, one TOTAL
control, 1,505 transactions and five exact extra duplicates, leaving 1,500
unique transactions. The raw control is 37,150 units and 65,924.67 in
discounts **before deduplication**. Five independently reconciled regional
amounts sum to 2,570,247.03; the source does not specify currency.

The meanings of exact duplicates, negative quantities and missing price
imputation are explicit **business assumptions**, not independently proven
historical facts. The model cannot silently change these policy choices.

## What still requires an explicit operator/security action

- Provision or rotate Railway reviewer code and scoped token; the connector
  can confirm variable names but never reads back their secret contents.
- Test a real *portal-triggered* workflow dispatch, separate from the
  already-proven automated draft PR creation.
- Configure GitHub branch rules and code review for changes to approved
  data policy and merges of generated candidate branches.
- For full OpenTelemetry traces and reliable model cost, configure a
  controlled exporter and usage receipts; this is separate from the accurate
  operation-level metrics already captured.

## Verified portal dispatch and current acceptance status (19 Nov 2026)

The production Railway protected endpoint accepted the one-time authenticated request and issued GitHub `workflow_dispatch` [#44501856719](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44501856719), confirming Railway → GitHub execution without revealing the reviewer code. That run exposed an actual GitHub skipped-job dependency: P5 accepted round 2 while Verifier and P4 were skipped. PR #40 fixes the transition, PR #41 prevents a false green verdict in the portal, and PR #42 adds a mandatory final job-level acceptance. A **new real full run** must confirm Verifier, P4, draft PR and separate exact-SHA CI after the fix. A green historical workflow without P4 is not acceptance.

The launcher permits up to five real `workflow_dispatch` attempts per rolling 24 hours, one active run, and a short server-side launch cooldown. The reviewer access code is a service-only Railway secret; it must not be committed to GitHub or inserted into public documentation.

## Recruiter real-time progress presentation

After private authorization, the portal displays the GitHub workflow link as soon as the dispatch is accepted, then binds the run to its exact correlation ID and public GitHub run ID. The reviewer sees actually observed Architect/Engineer/P3 retries/P5/Verifier/P4/P6/final-gate job results, the currently executing GitHub Actions step, elapsed time, failure or skipped phase labels, and a source link. A queued or not-yet-observed run is explicitly not represented as executing agents. A browser reload within the same tab retains only the random run/session ID and not the private reviewer code. When publication succeeds, the portal resolves the exact run's draft PR and its separate candidate exact-SHA CI state. Creating a draft PR is automatic after positive gates; merging remains human-reviewed. Timing is variable; the interface warns about multi-minute duration and possible long GitHub queues.

## Production acceptance confirmed: reviewer portal (19 November 2026)

A private reviewer code on Railway genuinely dispatched [GitHub Actions run #44509432197](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44509432197). Architect, Engineer (three candidate iterations), P3, P5, independent Verification Engineer, P4 positive and mutation tests, automatic draft-PR publisher, telemetry and the final fail-closed acceptance all completed successfully. This produced [draft PR #48](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/48) without requiring reviewer approval to create the PR. [Independent exact-SHA candidate CI #44512412721](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44512412721) is successful on the published candidate commit `fbebfefd7600f69d7b50507b4c9d0eb58f59a774`. The draft remains unmerged pending human code review. Historical source run #44485096373 / PR #35 remains an archived example, not the latest verified workflow.

A separate one-time push acceptance run #44508892159 was rejected by its mandatory terminal gate when the generated third candidate failed P3; this is expected fail-closed behavior. The previous long `pending` experience arose in part because the launcher checked only `workflow_dispatch` runs for concurrency even though one-time `push` acceptance used the same GitHub concurrency group. The corrected launch guard checks **all** active runs but counts only authenticated reviewer-dispatched runs toward the five-per-24-hour quota. The UI shows a source-grounded timeline and links the automatic draft PR as soon as GitHub publication is verified.
