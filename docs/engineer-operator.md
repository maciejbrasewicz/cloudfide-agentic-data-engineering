# P2 — Real Data Engineer in an isolated candidate workspace

This module implements the second LLM role in the approved CloudFide plan,
not a simulated code-review report. P1 Data Architect has passed the genuine
Foundry run 44413326286, with seven real tools and deterministic evidence.

## Launch

Open the trusted-main GitHub workflow:

https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/workflows/engineer-e2e.yml

Run workflow -> main -> mode=rebuild. The existing encrypted GitHub secret
CLOUDFIDE_TASK_SPEC_B64 is used privately; its value can be original UTF-8
or its Base64 encoding. The two jobs are:

1. Architect — rerun the original-task interpretation, produce the strict P1
   contract and validate source facts, decisions and real tool calls.
2. Engineer — download precisely that same-run Architect receipt, verify its
   SHA provenance, read the original task in memory and author actual candidate
   solution.py, pipeline.py, README.md and at least one tests/test_*.py file.

## Rebuild isolation

In rebuild mode there is NO existing solution.py or pipeline.py in the
workspace. Only original sales.csv, original test_virtual_column.py and
approved contracts/data_policy.json are copied into it. Generated edits
are restricted to solution.py, pipeline.py, README.md and flat
tests/test_*.py. No agent tool can edit employer fixtures, GitHub workflows,
dependencies, secrets or production code.

The Engineer receives the exact private task via a bounded read_spec tool,
and the contract via read_architect_contract. It must invoke
list_workspace, read_workspace_file, write_candidate_file, show_diff and
request_validation. Its final JSON must match the on-disk SHA-256 of every
claimed candidate artifact. A textual report without real writes FAILS.

## Meaning of P2 output

Download the p2-engineer-candidate-pending-sandbox artifact:

- candidate_bundle.zip: actual newly written code, tests and README, only
  allowlisted paths. NO private spec or cloud credentials.
- engineer_report.json: model explanation and actual-file SHA claims.
- engineer_gate.json: deterministic actual-write and tool execution verdict.
- validation_request.json: source hashes and a queued validation request.

Status CANDIDATE_READY_FOR_SANDBOX **does not mean this code works**. It
means only that the Engineer genuinely wrote files satisfying file/provenance
constraints. It must still go through P3 isolation, original pytest, Pandera,
independent Decimal revenue reconciliation and P4 adversarial Verifier tests.

No untrusted candidate Python is EVER executed in an Azure/OIDC job. P3 must
run in a separate no-secret, no-network container. Do not mark full autonomous
delivery as complete until P3–P7 and the ten E2E acceptance scenarios pass.
