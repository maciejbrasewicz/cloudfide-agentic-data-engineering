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

## C. GitHub → Foundry OIDC identity (after green CI)

Use [Microsoft Entra app registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade). Create an app such as `cloudfide-agent-review`, single tenant. Under **Certificates & secrets → Federated credentials → Add credential**, select **GitHub Actions deploying Azure resources**, then enter:

- GitHub organization/owner: `maciejbrasewicz`
- Repository: `cloudfide-agentic-data-engineering`
- Entity: **Branch**
- Branch: `main`

The trust subject should correspond to `repo:maciejbrasewicz/cloudfide-agentic-data-engineering:ref:refs/heads/main`. Do not create a client secret.

In Azure Portal, grant this application only the Foundry **User** role at the Foundry project and, if required for the chosen project endpoint, **Reader** on the Foundry resource. Actual available role names can reflect the ongoing Azure AI → Foundry renaming. Assign through Access Control (IAM), not by adding admin-level access. See [Foundry RBAC](https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry).

In GitHub repo **Settings → Secrets and variables → Actions → Variables**, add these **repository variables**:

| Variable | Value |
|---|---|
| `AZURE_CLIENT_ID` | Client (application) ID of the new Entra application |
| `AZURE_TENANT_ID` | `2fcd0468-9e97-4247-a52a-a7bc870ef450` |
| `AZURE_SUBSCRIPTION_ID` | Output of `az account show --query id -o tsv` on the right subscription |
| `FOUNDRY_PROJECT_ENDPOINT` | `https://registry9-claude-resource.services.ai.azure.com/api/projects/registry9-claude` |
| `FOUNDRY_MODEL` | `gpt-5.6-sol` |

Optional **Actions secret**: `APPLICATIONINSIGHTS_CONNECTION_STRING` to export traces. Omit it initially if Application Insights is not configured. This is separate from GitHub OIDC authentication.

## D. First cloud agent review

Go to GitHub **Actions → Foundry — evidence-bound multiagent review → Run workflow**, use the `main` branch. The workflow first runs deterministic tests, then signs in via OIDC, executes all three Foundry roles, validates the resulting artifact hashes, and uploads `foundry-agentic-review` for seven days.

A green AI review without tool calls in the trace is weaker evidence; inspect Foundry tracing (if enabled) and read the agent artifact. Findings are hypotheses until independently supported. **Never claim the review passed until Actions confirms it.**

## E. Final checklist before submission

- The repository contains *exact* required filenames and original inputs, not the original assignment PDF/Markdown.
- `uv.lock` committed; both OS checks are green.
- `revenue_by_region.csv` is deterministic and matches the committed artifact after rerun.
- README includes the source data issues, counts, assumptions and reproduction commands.
- The Foundry artifact is bound to a specific SHA/commit; no model output silently changes rules.
- Submit the GitHub URL through the CloudFide submission form before the email's 3-day deadline.
