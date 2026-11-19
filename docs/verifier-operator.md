# P4 — Real independent Verification Engineer and executable falsification

After the trusted P1 Data Architect, real P2 Data Engineer, up to three
evidence-driven P5 correction rounds and independent P3 sandbox verification,
P4 checks the ACTUAL successful candidate. It is the third Foundry role, not
a repurposed read-only code-review report.

## Flow

1. The P5 controller chooses the first **real PASSED P3 iteration** and
   publishes the selected candidate SHA and `WAITING_VERIFIER`. A rejected
   candidate cannot reach P4.
2. The trusted `verifier` job downloads only same-run artifacts, confirms
   the original private specification SHA, the P5 run ID and commit, P3
   independent receipt and original input fingerprints. It then invokes
   the real Foundry Verification Engineer.
3. The Verifier MUST use seven recorded tools: read the original assignment,
   employer tests and approved policy; read both generated Python modules;
   inspect the independent P3 receipt; create an actual pytest file via
   `write_adversarial_test`; and explicitly request separate execution.
   Its output is a SHA-bound proposed test, not proof that the test passed.
4. The `adversarial` job has `contents: read`, no Azure OIDC, no private
   original-task secret, no repo write rights. A trusted admission module
   validates exact candidate SHA, P3 receipt, the Verifier's test SHA and
   original test hashes before staging source.
5. **Positive control:** execute original employer tests, Engineer's own
   tests and the Verifier's newly authored test, then rerun the independent
   raw CSV + Decimal oracle on the resulting revenue file.
6. **Negative control:** copy the candidate into a second isolated workspace,
   replace only its virtual-column function with a deliberately broken
   always-empty implementation and run **only the newly authored Verifier
   test**, not the employer's tests. It MUST fail.
7. The trusted host receipt records `PASSED` only if the real candidate,
   independent financial oracle and mutation sensitivity all pass. Otherwise
   the result is `REWORK_REQUIRED`, `WEAK_VERIFIER_TEST` or
   `INFRA_FAILURE`. All real logs and artifacts are retained.

The two Docker executions use a static pinned-dependency image, no network,
read-only mounts and root, a nonroot UID, dropped capabilities, process
and resource limits. No model-generated Python executes in the job that holds
Azure credentials.

## One-click execution

Run the existing unified workflow:

https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/workflows/engineer-e2e.yml

Select branch `main`, mode `rebuild`, maximum attempts `1` to `3`.
The workflow now includes P4 after the selected P5 result is
`WAITING_VERIFIER`. In its Actions page, inspect:

- `p4-verifier-evidence`: role output, test source, actual tool-call gate.
- `p4-independent-adversarial-validation`: positive and negative real test
  logs, original financial reconciliation and exact verdict.

**P4 PASSED is not a final delivery PR.** The only approved downstream
actions remain P6 creation of a human-reviewed draft PR, explicit CI on
the exact commit and never auto-merge.
