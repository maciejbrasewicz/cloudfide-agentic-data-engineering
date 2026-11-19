# P3 — Candidate execution and independent finance reconciliation

P3 is the first component authorized to execute any Data Engineer-written Python.
It runs as a THIRD job in the already existing real Foundry Architect -> Engineer
GitHub workflow. The job has only GitHub contents:read, NO id-token write,
NO Azure login and NO private original-task secret.

## Trust boundary

The trusted runner first verifies both SHA-256 lists in the P2 Engineer gate
and the P2 validation request, then independently compares all three original
input fingerprints against the checked-out original source. It rejects ZIP
entries outside solution.py, pipeline.py, README.md and flat tests/test_*.py,
duplicate filenames, symbolic links, oversized files and any mismatched bytes.
No model-generated Python is executed during this admission stage.

A static, source-reviewed Dockerfile is built from only the trusted sandbox/
directory. The generated ZIP is NEVER included in the Docker build context.

The resulting container is executed with:
- no network;
- read-only root filesystem, read-only candidate input mount;
- non-root UID, all Linux capabilities dropped, no-new-privileges;
- limited CPU, memory, processes and ephemeral tmpfs;
- exactly one writable output folder containing test logs, result CSV and
  numerical exit codes; no Azure credentials or GitHub write token.

Its immutable run-candidate.sh first executes employer and model-written
pytest tests, then invokes pipeline.py with explicit input/output paths.
The runner records ACTUAL exit codes. It never declares success itself.

## Independent, host-side verdict

After the Docker process exits, trusted agentic.p3_oracle computes original
regional totals from the supplied CSV with Python stdlib csv and Decimal.
It does NOT import or call the generated candidate, nor the production pandas
pipeline. It independently reconciles original TOTAL before deduplication,
identifies original exact duplicate lines, applies the approved price/return
assumptions and compares five sorted regional totals and output schema.
A failed pytest command, failed pipeline command or wrong result fails the job.

Output artifacts named p3-independent-sandbox-validation:
- admission.json — verified P2 file/input fingerprints;
- verification.json — independent PASSED / FAILED decision;
- tests.log, pipeline.log, actual exit-code receipts;
- revenue_by_region.csv only when candidate produced it.

**P3 PASSED does not mean P4 Verification Engineer completed.** The separate
Verifier must still construct and execute original, independent falsification
tests. P5 will add a bounded controller to send P3/P4 counterexamples back to
the Engineer for real code changes. No auto-merge or policy approval occurs.

## Launch

Run the same workflow:

https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/workflows/engineer-e2e.yml

Select main and rebuild. It performs P1 -> P2 -> P3 in three isolated jobs.
The source code in main and the original employer fixtures are unchanged.
