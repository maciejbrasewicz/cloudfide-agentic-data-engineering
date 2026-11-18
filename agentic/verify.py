"""Independent provenance gate for a Foundry review artifact.

Model-produced findings are *not* treated as certified facts. This gate only
attests to the source, policy, output and audit that the agents reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from .models import ReviewReport
from pipeline import ROOT


EXPECTED_ROLES = ("data_architect", "data_engineer", "verification_engineer")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_provenance(root: Path = ROOT) -> dict[str, str]:
    """Pin all artifacts material to the correctness of this specific task."""
    artifacts = {
        "source_sha256": root / "sales.csv",
        "output_sha256": root / "revenue_by_region.csv",
        "policy_sha256": root / "contracts" / "data_policy.json",
        "audit_sha256": root / "reports" / "data_quality.json",
        "solution_sha256": root / "solution.py",
        "pipeline_sha256": root / "pipeline.py",
        "tests_sha256": root / "test_virtual_column.py",
    }
    artifacts.update({
        "agent_workflow_sha256": root / "agentic" / "run.py",
        "agent_tools_sha256": root / "agentic" / "tools.py",
        "agent_models_sha256": root / "agentic" / "models.py",
        "package_manifest_sha256": root / "pyproject.toml",
    })
    if (root / "uv.lock").exists():
        artifacts["dependency_lock_sha256"] = root / "uv.lock"
    hashes = {key: sha256(path) for key, path in artifacts.items()}
    suite = hashlib.sha256()
    for path in sorted((root / "tests").glob("test_*.py")):
        suite.update(path.relative_to(root).as_posix().encode("utf-8"))
        suite.update(b"\0")
        suite.update(path.read_bytes())
    hashes["test_suite_sha256"] = suite.hexdigest()
    return hashes


def verify_manifest(manifest: dict, root: Path = ROOT) -> dict:
    """Fail on stale artifacts, missing participants or malformed agent output."""
    reports = [ReviewReport.model_validate(entry) for entry in manifest["agent_reviews"]]
    if tuple(report.role for report in reports) != EXPECTED_ROLES:
        raise ValueError("Incorrect number or order of agent reviews")
    claimed = manifest["provenance"]
    recorded_revision = manifest.get("git_revision")
    current_revision = os.getenv("GITHUB_SHA")
    if not current_revision and (root / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True,
                capture_output=True, timeout=5, check=False,
            )
            if result.returncode == 0:
                current_revision = result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    if recorded_revision and current_revision and recorded_revision != current_revision:
        raise ValueError("Agent report was produced for a different git revision")
    measured = collect_provenance(root)
    if claimed != measured:
        changed = sorted(key for key in measured if claimed.get(key) != measured[key])
        raise ValueError(f"Agent report provenance is stale: {changed}")

    audit = json.loads((root / "reports/data_quality.json").read_text(encoding="utf-8"))
    for key in ("source_sha256", "output_sha256", "policy_sha256"):
        if audit.get(key) != measured[key]:
            raise ValueError(f"Stale deterministic ETL audit: {key}")
    if audit.get("reconciliation_status") != "passed":
        raise ValueError("ETL reconciliation does not pass")
    if audit.get("transactions_after_dedup") != 1500:
        raise ValueError("Unexpected transaction count for provided fixture")

    return {
        "provenance_matched": True,
        "three_structured_agent_reports": True,
        "deterministic_reconciliation_confirmed": True,
        "agent_findings_remain_untrusted": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a Foundry review against current checked-out files")
    parser.add_argument("--input", type=Path, default=ROOT / "agentic_review_runtime.json")
    args = parser.parse_args()
    manifest = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(verify_manifest(manifest), indent=2))


if __name__ == "__main__":
    main()
