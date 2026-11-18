"""Bounded multiagent Foundry review of the *same* CloudFide ETL deliverable.

Run: python -m agentic.run --task-file /path/to/taskvirtualcolumn.md
Requires Azure credentials and a Foundry project deployment; no agent keys in Git.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from .models import parse_report
from .verify import collect_provenance, verify_manifest
from .tools import (
    check_quality, inspect_approved_policy, inspect_orders, inspect_reconciliation,
    profile_source, read_project_file,
)
from pipeline import ROOT


ARCHITECT = """You are an evidence-first Data Architect for a pandas Data Engineering task.
Use profile_source and inspect_orders before making claims. Distinguish facts from assumptions.
Review all input-cleaning rules: repeated headers, TOTAL source control, exact duplicates,
negative quantity, mixed numeric formats, missing unit prices, regional normalization.
Evaluate whether the *existing* approved data contract is justified by evidence.
Do not modify any file. Do not invent counts. All discovered issues must reference evidence.
Return ONLY JSON matching: {"role":"data_architect","summary":"...","findings":[{"category":
"source_data","severity":"medium","statement":"...","evidence":"...",
"suggested_verification":"..."}],"recommended_next_action":"..."}.
"""
ENGINEER = """You are a senior Data Engineer auditing an actual Python/pandas implementation.
Read solution.py, pipeline.py, contracts/data_policy.json, and tests. Call check_quality.
Check that the code satisfies the exact task and implements decisions justified by the architect.
Suggest minimal source changes only if demonstrably needed. You have read-only tools.
Never claim a change has been made. Do not write or execute arbitrary code.
Return ONLY JSON with keys role='data_engineer', summary, findings (same fields as architect),
and recommended_next_action; maximum 12 well-evidenced findings.
"""
VERIFIER = """You are an independent and skeptical Verification Engineer.
Use inspect_reconciliation, check_quality, and read_project_file. Look for errors in the previous
agents' assertions, tests that only assert their own generated output, and weak data assumptions.
Your job is to attempt to FALSIFY correctness; do not approve on the basis of other agent opinions.
Do not change files. If you cannot prove a claim, label it unverified in your statement.
Return ONLY JSON with role='verification_engineer', summary, findings (category, severity,
statement, evidence, suggested_verification), recommended_next_action.
"""


def setup_tracing() -> None:
    connection = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    if connection:
        from microsoft.opentelemetry import use_microsoft_opentelemetry
        use_microsoft_opentelemetry(
            enable_azure_monitor=True,
            azure_monitor_connection_string=connection,
            sampling_ratio=1.0,
            enable_sensitive_data=False,
            instrumentation_options={"agent-framework": {"enabled": True, "agent_name": "CloudFideETLReview"}},
        )


async def perform(task_file: Path | None) -> dict:
    from agent_framework import Agent
    from agent_framework.foundry import FoundryChatClient
    from agent_framework.orchestrations import SequentialBuilder
    from azure.identity import DefaultAzureCredential

    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    model = os.environ.get("FOUNDRY_MODEL")
    if not endpoint or not model:
        raise RuntimeError("Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL (see .env.example)")

    task_context = ""
    if task_file:
        task_context = task_file.read_text(encoding="utf-8")[:20_000]

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    client = FoundryChatClient(project_endpoint=endpoint, model=model, credential=credential)
    architect = Agent(name="data_architect", client=client, instructions=ARCHITECT,
                      tools=[profile_source, inspect_orders, inspect_approved_policy])
    engineer = Agent(name="data_engineer", client=client, instructions=ENGINEER,
                     tools=[read_project_file, check_quality, inspect_approved_policy])
    verifier = Agent(name="verification_engineer", client=client, instructions=VERIFIER,
                     tools=[read_project_file, inspect_reconciliation, check_quality])

    workflow = SequentialBuilder(participants=[architect, engineer, verifier], output_from="all").build()
    prompt = (
        "Analyze and independently review this actual Data Engineering deliverable, from input anomalies "
        "to final CSV, policy, implementation, documentation and tests. "
        "Return JSON in each agent's prescribed schema. The repository is read-only. "
        "Original task source (provided privately, do not commit it):\n" + task_context
    )
    response = await workflow.run(prompt)
    outputs = list(response.get_outputs())
    if len(outputs) != 3:
        raise RuntimeError(f"Expected exactly three agent responses, got {len(outputs)}")
    reports = [parse_report(part.text) for part in outputs]
    expected = ["data_architect", "data_engineer", "verification_engineer"]
    if [part.role for part in reports] != expected:
        raise RuntimeError("Wrong agent output order or role: fail closed")
    git_revision = os.getenv("GITHUB_SHA")
    if not git_revision:
        try:
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                capture_output=True, timeout=5, check=False,
            )
            git_revision = revision.stdout.strip() if revision.returncode == 0 else None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            git_revision = None
    manifest = {
        "schema_version": 2,
        "git_revision": git_revision,
        "provenance": collect_provenance(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_deployment": model,
        "foundry_project_endpoint_present": True,
        "reports_are_untrusted_suggestions": True,
        "agent_reviews": [part.model_dump(mode="json") for part in reports],
    }
    manifest["deterministic_attestation"] = verify_manifest(manifest)
    return manifest


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", type=Path, help="Optional original instructions outside the repository")
    parser.add_argument("--output", type=Path, default=ROOT / "agentic_review_runtime.json")
    args = parser.parse_args()
    setup_tracing()
    result = asyncio.run(perform(args.task_file))
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Three Foundry agent reviews completed: {args.output}")


if __name__ == "__main__":
    main()
