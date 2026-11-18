# Deployment runbook — CloudFide engineering evidence

This repo deliberately has **no long-running cloud service**. GitHub Actions executes the deterministic ETL and the optional Foundry multiagent audit. Azure tokens are obtained via Entra ID, never committed.

## A. Local Windows validation (VS Code PowerShell)

1. Keep `.env` in project root with:

   ```dotenv
   FOUNDRY_PROJECT_ENDPOINT=https://YOUR-RESOURCE.services.ai.azure.com/api/projects/YOUR-PROJECT
   FOUNDRY_MODEL=YOUR-DEPLOYMENT-NAME
   APPLICATIONINSIGHTS_CONNECTION_STRING=
   ```

2. From the root, using Python 3.12 and `uv`:

   ```powershell
   uv lock
   uv sync --locked --extra quality --extra foundry
   uv run --no-sync python -m ruff check solution.py pipeline.py contracts.py agentic tests
   uv run --no-sync python -m pytest
   uv run --no-sync python pipeline.py
   ```

3. Re-run the actual three-agent review **after** changes to the code, contract or tests:

   ```powershell
   uv run --no-sync python -m agentic.run --task-file "C:\path\outside\repo\taskvirtualcolumn.md"
   uv run --no-sync python -m agentic.verify --input agentic_review_runtime.json
   ```

   Keep the provided task instructions outside the submitted repo. A passed attestation means that the report applies to the current artifact hashes; it is **not** an LLM correctness endorsement.

## B. GitHub delivery and deterministic CI

The project has already been published to [the GitHub repository](https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering). Both `windows-latest` and `ubuntu-latest` are checked automatically on each push. The supplied fixtures are preserved byte-for-byte, and CI installs pinned dependencies from `uv.lock`. No local Git or GitHub CLI is needed to review or run it.

## C. One-time GitHub → Microsoft Foundry authentication

Deterministic CI requires no Azure credentials and is already green on Windows and Linux.

The optional cloud-based agent review needs a dedicated Microsoft Entra service principal.
With Azure CLI authenticated in the tenant that owns the Foundry project, run the
[repository bootstrap script](../scripts/setup-foundry-oidc.ps1) from PowerShell:

```powershell
Invoke-WebRequest "https://raw.githubusercontent.com/maciejbrasewicz/cloudfide-agentic-data-engineering/main/scripts/setup-foundry-oidc.ps1" -OutFile "$env:TEMP\cloudfide-oidc.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\cloudfide-oidc.ps1"
```

The script discovers the resource subscription, registers an OIDC app, grants Foundry
User at the project scope, and prints **non-secret** client/tenant/subscription IDs.
It uses GitHub's *immutable* owner/repository OIDC subject (appropriate for newly
created repositories after July 2026), not the old name-only subject. No client secret.

GitHub Actions consumes these non-secret identifiers plus the Foundry project endpoint
and model deployment name. The assistant can update the workflow and inspect logs via
the connected GitHub service, but it cannot operate the user's Azure CLI session
from this chat. Entra setup must run once from an authorized Azure account.

The optional Application Insights connection string must stay a secret. Do not commit
it or the local .env file.

## D. Agent review and evidence

Once OIDC is configured, execute the manual `agent-review.yml` workflow (or trigger
it through a temporary scoped push trigger). It executes deterministic quality checks
first, then invokes the Foundry agents using the federated Entra identity.
The resulting provenance report links the analyzed data, code, policy, tests and
output by SHA-256. It does *not* certify that every statement from an LLM is correct.

## E. Final checklist before submission

- The repository contains *exact* required filenames and original inputs, not the original assignment PDF/Markdown.
- `uv.lock` committed; both OS checks are green.
- `revenue_by_region.csv` is deterministic and matches the committed artifact after rerun.
- README includes the source data issues, counts, assumptions and reproduction commands.
- The Foundry artifact is bound to a specific SHA/commit; no model output silently changes rules.
- Submit the GitHub URL through the CloudFide submission form before the email's 3-day deadline.
