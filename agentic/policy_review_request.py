"""Independently validate Architect policy exceptions and request HUMAN approval.

This module never applies a policy change or imports generated candidate code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from contracts import DataPolicy, read_policy
from .policy_gate import REQUIRED_TOOLS


class PolicyReviewError(ValueError):
    """The policy change request lacks verified original source provenance."""


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PolicyReviewError("Expected structured policy evidence")
    return value


def prepare_human_review(evidence: Path, root: Path, run_id: str) -> str | None:
    """Build a human-readable issue only for exact SHA-validated policy changes."""
    gate_path = evidence / "architect_gate.json"
    if not gate_path.is_file():
        return None
    gate = _read(gate_path)
    if gate.get("status") != "AWAITING_HUMAN_APPROVAL":
        return None
    if not run_id.isdecimal() or len(run_id) > 30:
        raise PolicyReviewError("Invalid source run ID")
    manifest = _read(evidence / "input_manifest.json")
    contract = _read(evidence / "contract_proposal.json")
    baseline_path = root / "contracts/data_policy.json"
    baseline_sha = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    approved = read_policy(baseline_path).model_dump(mode="json")
    proposal = DataPolicy.model_validate(contract["proposed_policy"]).model_dump(mode="json")
    independent_diff = {
        k: {"approved": str(approved[k]), "proposed": str(v)}
        for k, v in proposal.items() if approved[k] != v
    }
    if (
        not independent_diff or independent_diff != gate.get("policy_diff")
        or gate.get("failures") != []
        or set(gate.get("verified_tool_calls", [])) != REQUIRED_TOOLS
        or manifest.get("approved_policy_sha256") != baseline_sha
        or gate.get("source_sha256") != manifest.get("source_csv_sha256")
        or contract.get("source_sha256") != manifest.get("source_csv_sha256")
        or gate.get("task_spec_sha256") != manifest.get("specification_sha256")
        or contract.get("specification_sha256") != manifest.get("specification_sha256")
        or manifest.get("run_id") != run_id
    ):
        raise PolicyReviewError("Untrusted Architect policy change lineage")
    lines = [
        "# Data policy proposal — human decision required",
        "",
        "**NOT APPROVED.** No model or automation may apply this proposal.",
        "",
        f"Actual source run: https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/{run_id}",
        f"Original CSV SHA-256: {manifest['source_csv_sha256']}",
        f"Previously approved policy SHA-256: {baseline_sha}",
        f"Original private task SHA-256 (text not disclosed): {manifest['specification_sha256']}",
        "",
        "| Field | Existing approved value | Proposed unapproved value |",
        "|---|---|---|",
    ]
    for field, values in sorted(independent_diff.items()):
        lines.append(f"| {field} | {values['approved']} | {values['proposed']} |")
    lines.extend([
        "",
        "## Required human action",
        "",
        "1. Inspect the underlying source and independently assess the business meaning.",
        "2. To reject: close this issue with a reason. No data policy is changed.",
        "3. To approve: open a separate PR modifying contracts/data_policy.json.",
        "4. Include the business rationale and independent tests for each changed field.",
        "5. Require a human code review, merge on trusted main, and rerun Architect.",
        "",
        "A GitHub issue or a model proposal is NEVER an executable policy approval.",
        "This issue contains no original private task text, model prompt, or secret.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--architect-evidence", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    text = prepare_human_review(args.architect_evidence, args.root, args.run_id)
    if text is None:
        print("No valid policy proposal; no automatic approval or issue")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print("Human policy decision required; proposal NOT APPROVED")


if __name__ == "__main__":
    main()
