"""Execute a REAL Foundry Data Architect with bounded read-only source tools.

The model can propose policy changes but only independent Python checks may
advance the process. Original task instructions are read at runtime, never
committed or included in the input manifest.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from contracts import DataPolicy, read_policy
from pipeline import ROOT

from .input_manifest import create_input_manifest, verify_unchanged_inputs
from .policy_gate import ArchitectToolLedger, evaluate_architect, policy_sha
from .schemas.architect import ArchitectReport
from .source_tools import inspect_original_order_ids, original_tests, source_facts
from .spec_loader import TaskSpec, load_task_spec


def build_architect_tools(
    *, spec: TaskSpec, root: Path, ledger: ArchitectToolLedger,
):
    """Construct SDK tools using trusted closures, not model-supplied file paths."""
    from agent_framework import tool

    @tool(approval_mode="never_require")
    def read_spec() -> str:
        """Read the original recruitment task privately, with its SHA-256."""
        value = json.dumps({"sha256": spec.sha256, "text": spec.text}, ensure_ascii=False)
        ledger.record("read_spec")
        return value

    @tool(approval_mode="never_require")
    def inspect_original_tests() -> str:
        """Read the exact supplied virtual-column tests, not existing solution code."""
        result = json.dumps(original_tests(root), ensure_ascii=False)
        ledger.record("inspect_original_tests")
        return result

    @tool(approval_mode="never_require")
    def profile_source() -> str:
        """Count anomalies in raw CSV with independent stdlib parsing."""
        result = source_facts(root).model_dump_json()
        ledger.record("profile_source")
        return result

    @tool(approval_mode="never_require")
    def inspect_orders(order_ids: str) -> str:
        """Inspect 1-10 real source order IDs, formatted as comma-separated SO-xxxxx."""
        result = inspect_original_order_ids(root, order_ids)
        ledger.record("inspect_orders")
        return result

    @tool(approval_mode="never_require")
    def reconcile_raw_control() -> str:
        """Verify the raw TOTAL before deduplication; fail on disagreement."""
        facts = source_facts(root)
        result = json.dumps({
            "source_sha256": facts.source_sha256,
            "transaction_rows": facts.transaction_rows,
            "raw_quantity_total": facts.raw_quantity_total,
            "control_quantity": facts.control_quantity,
            "raw_discount_total": facts.raw_discount_total,
            "control_discount": facts.control_discount,
            "control_reconciled": facts.control_reconciled,
        })
        ledger.record("reconcile_raw_control")
        return result

    @tool(approval_mode="never_require")
    def inspect_approved_policy() -> str:
        """Read the currently authorized version of the deterministic data policy."""
        policy = read_policy(root / "contracts/data_policy.json")
        result = json.dumps({
            "status": "approved_baseline_v1",
            "policy_sha256": policy_sha(policy),
            "policy": policy.model_dump(mode="json"),
        })
        ledger.record("inspect_approved_policy")
        return result

    @tool(approval_mode="never_require")
    def validate_policy_proposal(proposed_policy_json: str) -> str:
        """Validate a proposed policy against fixed Pydantic choices; do NOT approve."""
        proposal = DataPolicy.model_validate_json(proposed_policy_json)
        baseline = read_policy(root / "contracts/data_policy.json")
        delta = {
            key: {"approved": str(getattr(baseline, key)), "proposed": str(value)}
            for key, value in proposal.model_dump(mode="json").items()
            if value != getattr(baseline, key)
        }
        ledger.record_validated_policy(proposal)
        return json.dumps({
            "validation": "schema_valid_not_approved",
            "proposed_policy_sha256": policy_sha(proposal),
            "requires_human_approval": bool(delta),
            "changes": delta,
        })

    return [
        read_spec, inspect_original_tests, profile_source,
        inspect_orders, reconcile_raw_control, inspect_approved_policy,
        validate_policy_proposal,
    ]


def _instructions() -> str:
    schema = ArchitectReport.model_json_schema()
    return (
        "You are Data Architect 01 in a controlled, evidence-bound CloudFide "
        "Data Engineering delivery pipeline. You are designing the implementation "
        "contract, NOT reviewing or copying any existing source solution.\n"
        "FIRST call read_spec and inspect_original_tests. Then call profile_source, "
        "reconcile_raw_control, inspect_approved_policy and inspect_orders on real "
        "SO- order IDs. BEFORE your final response, call validate_policy_proposal "
        "with the complete proposed policy JSON. Every one of these seven tool "
        "calls is mandatory and is independently audited.\n"
        "Identify all three parts of the actual task: safe arithmetic virtual "
        "columns, sales CSV ETL, tests and README. The requirements must contain "
        "exactly these six keys: virtual_column, invalid_expressions, "
        "source_cleaning, revenue_formula, regional_aggregation, tests_and_readme. "
        "Each requirement must cite task_spec; virtual_column and "
        "invalid_expressions must also cite original_tests.\n"
        "Copy only facts actually returned by profile_source into observed_facts; "
        "keep every field and value exactly. Confirm raw TOTAL before dropping "
        "any duplicates. Distinguish explicitly specified empty discounts from "
        "UNVERIFIED business assumptions about duplicate removal, negative "
        "quantities and historical unit prices. Never claim source data proves "
        "those assumptions.\n"
        "Return exactly six decisions, for source_control, duplicates, "
        "negative_quantity, missing_unit_price, missing_discount and region. "
        "Evidence refs are task_spec, original_tests, source_profile, "
        "source_controls, inspected_orders and approved_policy. For duplicates "
        "cite source_profile AND source_controls. Proposed_value must match "
        "the proposed_policy field. Classification: source_control=data_integrity, "
        "duplicates/negative_quantity/missing_unit_price=business_assumption, "
        "missing_discount=specified, region=repair_policy.\n"
        "Model output is a proposal, never policy approval. If approved v1 rules "
        "are compatible with the assignment, keep them and record their unresolved "
        "semantic risks. If you propose a changed rule, the controller will halt "
        "for human approval. Do not fabricate measurements, create code, read "
        "solution.py, or run arbitrary commands.\n"
        "FINAL RESPONSE MUST BE ONE JSON OBJECT MATCHING THIS EXACT SCHEMA "
        "without markdown or commentary:\n" + json.dumps(schema)
    )


async def execute_architect(
    *, spec: TaskSpec, root: Path,
    ledger: ArchitectToolLedger,
    endpoint: str, model: str,
) -> str:
    """Run one actual Foundry agent with ONLY the seven scoped tools."""
    from agent_framework import Agent
    from agent_framework.foundry import FoundryChatClient
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    client = FoundryChatClient(
        project_endpoint=endpoint, model=model, credential=credential,
    )
    config = getattr(client, "function_invocation_configuration", None)
    if config is not None:
        config.update({
            "max_iterations": 15,
            "max_function_calls": 24,
            "max_duration_seconds": 180,
            "allow_concurrent_invocation": False,
        })
    agent = Agent(
        name="data_architect",
        client=client,
        instructions=_instructions(),
        tools=build_architect_tools(spec=spec, root=root, ledger=ledger),
    )
    response = await agent.run(
        "Prepare the evidence-bound Data Engineering architecture and policy "
        "proposal from the REAL original assignment and original source files. "
        "Invoke every mandatory tool. Your task specification SHA-256 is "
        + spec.sha256 + ". Return the structured contract JSON only."
    )
    return response.text or ""


def _write_json(path: Path, data: dict) -> None:
    """Write an artifact atomically; never persist the original specification."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix=".architect-", suffix=".json", delete=False,
    ) as target:
        temporary = Path(target.name)
        json.dump(data, target, ensure_ascii=False, indent=2)
        target.write("\n")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Real Foundry Data Architect with evidence gates")
    parser.add_argument("--task-file", type=Path, default=None,
                        help="Original task file outside this repo (local only)")
    parser.add_argument("--mode", choices=("rebuild", "improve"), default="rebuild")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "architect-evidence")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    # Secrets must be provided via GitHub Actions secrets or an external local file.
    spec = load_task_spec(
        repo_root=ROOT, path=args.task_file,
        encoded=os.getenv("CLOUDFIDE_TASK_SPEC_B64") or None,
    )
    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    model = os.getenv("FOUNDRY_MODEL")
    if not endpoint or not model:
        raise SystemExit("Foundry deployment configuration is missing")

    trusted = source_facts(ROOT)
    approved = read_policy(ROOT / "contracts/data_policy.json")
    manifest = create_input_manifest(
        root=ROOT, spec=spec, mode=args.mode,
        base_commit=os.environ.get("GITHUB_SHA") or _local_commit(),
        model_deployment=model,
        run_id=os.environ.get("GITHUB_RUN_ID"),
    )
    ledger = ArchitectToolLedger()
    raw_response = asyncio.run(execute_architect(
        spec=spec, root=ROOT, ledger=ledger, endpoint=endpoint, model=model,
    ))
    verify_unchanged_inputs(ROOT, manifest)
    if source_facts(ROOT) != trusted:
        raise SystemExit("Original source changed during Architect execution")

    try:
        report = ArchitectReport.model_validate_json(raw_response.strip())
    except ValueError:
        # Never log a model response containing private task text on schema failure.
        raise SystemExit("Architect output did not match the strict report schema") from None

    receipt = evaluate_architect(
        report, trusted_facts=trusted,
        task_spec_sha256=spec.sha256, approved_policy=approved,
        tool_ledger=ledger,
    )
    output = args.output_dir
    _write_json(output / "architect_report.json", report.model_dump(mode="json"))
    _write_json(output / "contract_proposal.json", {
        "source_sha256": trusted.source_sha256,
        "specification_sha256": spec.sha256,
        "proposed_policy": report.proposed_policy.model_dump(mode="json"),
        "decisions": [item.model_dump(mode="json") for item in report.decisions],
    })
    _write_json(output / "architect_gate.json", receipt.model_dump(mode="json"))
    _write_json(output / "input_manifest.json", manifest.model_dump(mode="json"))
    print(json.dumps({
        "status": receipt.status, "requirements": len(report.requirements),
        "verified_tool_calls": len(receipt.verified_tool_calls),
        "failures": receipt.failures, "policy_changes": list(receipt.policy_diff),
        "output_dir": str(output),
    }))
    if receipt.status != "APPROVED_FOR_ENGINEERING":
        raise SystemExit(2)


def _local_commit() -> str:
    import subprocess

    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        text=True, capture_output=True, timeout=5, check=True,
    )
    return proc.stdout.strip()


if __name__ == "__main__":
    main()
