# P5 — Evidence-driven bounded rework after independent sandbox failure

This stage closes the real, demonstrated loop between P2 Data Engineer and the
independent P3 sandbox. It never "fixes" the model-generated code manually.
The first real P3 run [#44427435012](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44427435012)
returned **16 passing and 2 failing tests**, both proving that whitespace
at the start of a virtual-column expression was incorrectly rejected.

## What happens on P3 FAILED

The P3 job always publishes a machine-readable validation receipt. A
candidate failure is recorded as `FAILED` in that receipt (without pretending
it passed); failure to download, build, or run the independent container is
classified separately as infrastructure trouble.

The workflow condition starts a second trusted Azure OIDC Data Engineer job
only after it sees a genuine P3 `FAILED` receipt. The Engineer gets:

- original private CloudFide task at runtime;
- the previously accepted Data Architect report and immutable policy;
- the *previous generated* implementation from the P2 SHA-verified artifact,
  **not** the existing production implementation from main;
- the genuine failing pytest traceback and exit codes from the no-secret
  sandbox, exposed as a read-only feedback tool.

The Engineer must actually read the failure evidence and both previous Python
files, write complete new candidate files (including tests and README),
show a diff and request validation. Its old-vs-new hash manifest is verified.
Same bytes, missing actual tool calls, missing original fixtures or unsupported
policy changes fail the rework gate.

## Independent retest

A fresh `sandbox-rework-r2` job has **no Azure OIDC or private assignment
secret**, again admitting only approved ZIP bytes and running the same
no-network, nonroot, read-only Docker and independent stdlib Decimal oracle.
The resulting artifact is `p5-sandbox-r2-validation`.

A passing second candidate is not automatically merged and still requires
P4 independent adversarial Verifier tests, P6 publishing and final acceptance.

## Status and expansion

The current implementation permits **one repair attempt after the initial
candidate**. The approved architecture allows **up to three total candidate
attempts**; third-round retry and the deterministic final controller will be
integrated after the actual second-round P3 result is verified. A run that
exhausts the configured limit must produce REJECTED and a reproducible reason,
never a fabricated PASS.

The canonical operator trigger remains:

https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/workflows/engineer-e2e.yml
