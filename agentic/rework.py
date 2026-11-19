"""P5 bounded rework: real Foundry Engineer repairs a failed sandbox candidate.

Trusted feedback is read from a failed P3 run, the previous candidate is
verified against its original SHA receipts, and the model must WRITE a fresh
complete candidate. No model-produced Python is executed in this Azure job.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from pipeline import ROOT
from .candidate_intake import verify_and_stage_candidate
from .engineer import (
    _atomic_json, _export_files, engineer_tools, instructions, verified_architect,
)
from .engineer_gate import EngineerLedger, evaluate_engineer
from .schemas.architect import ArchitectReport
from .schemas.engineer import EngineerReport
from .spec_loader import TaskSpec, load_task_spec
from .workspace import CandidateWorkspace, create_workspace

_MAX_FEEDBACK = 13_000


class ReworkInputError(ValueError):
    """Previous candidate was not genuinely executed or not a known code failure."""


@dataclass
class ReworkLedger:
    read_failure: bool = False
    previous_reads: set[str] = field(default_factory=set)


def verified_failed_candidate(
    *, previous_dir: Path, p3_dir: Path, stage: Path,
) -> tuple[dict, dict, dict, str]:
    """Require a real failed sandbox receipt tied to the exact prior candidate."""
    gate = json.loads((previous_dir / "engineer_gate.json").read_text(encoding="utf-8"))
    request = json.loads((previous_dir / "validation_request.json").read_text(encoding="utf-8"))
    verification_raw = (p3_dir / "verification.json").read_bytes()
    outcome = json.loads(verification_raw.decode("utf-8"))
    if outcome.get("status") != "FAILED" or outcome.get("source") != "independent_p3_stdlib_oracle":
        raise ReworkInputError("Previous independent P3 verdict was not FAILED")
    # A command that never started or missing exit-code artifacts is an infra
    # incident, not evidence that candidate source code needs rework.
    try:
        test_exit = int((p3_dir / "test_exit_code.txt").read_text(encoding="utf-8").strip())
        pipeline_exit = int((p3_dir / "pipeline_exit_code.txt").read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        raise ReworkInputError("Missing real container exit codes; classify as INFRA_FAILURE") from exc
    if not 0 <= test_exit <= 255 or not 0 <= pipeline_exit <= 255:
        raise ReworkInputError("Invalid sandbox exit-code receipt")
    if test_exit == 0 and pipeline_exit == 0 and "reconciliation" not in outcome.get("failure", "").lower():
        raise ReworkInputError("Previous sandbox succeeded; no reproducible defect for rework")
    admission = json.loads((p3_dir / "admission.json").read_text(encoding="utf-8"))
    staged = verify_and_stage_candidate(
        archive_path=previous_dir / "candidate_bundle.zip",
        engineer_gate=gate, validation_request=request,
        original_checkout=ROOT, destination=stage,
    )
    if admission != staged:
        raise ReworkInputError("P3 admission does not match original candidate and fixtures")
    from .verifier_gate import candidate_manifest_digest
    return outcome, gate, staged, candidate_manifest_digest(staged["files"])


def rework_tools(
    *, spec: TaskSpec, architect: ArchitectReport, workspace: CandidateWorkspace,
    engineer_ledger: EngineerLedger, rework_ledger: ReworkLedger,
    prior_root: Path, verdict: dict, feedback_dir: Path,
):
    """Extend the seven real writing tools with two read-only failure tools."""
    from agent_framework import tool

    original_tools = engineer_tools(
        spec, architect, workspace, engineer_ledger, architect_digest="",
    )

    @tool(approval_mode="never_require")
    def read_failure_evidence() -> str:
        """Read measured sandbox failures and original failing test traceback."""
        evidence = {
            "p3_verdict": verdict,
            "tests_log": _bounded_log(feedback_dir / "tests.log"),
            "pipeline_log": _bounded_log(feedback_dir / "pipeline.log"),
        }
        rework_ledger.read_failure = True
        return json.dumps(evidence, ensure_ascii=False)

    @tool(approval_mode="never_require")
    def read_previous_candidate(relative_path: str) -> str:
        """Read a genuine previous candidate file, never the working repo solution."""
        if relative_path not in {"solution.py", "pipeline.py", "README.md"} and not (
            relative_path.startswith("tests/test_") and relative_path.endswith(".py")
            and "/" not in relative_path[6:]
        ):
            raise ReworkInputError("Previous candidate path not allowed")
        path = prior_root / relative_path
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(prior_root.resolve()):
            raise ReworkInputError("Previous candidate path missing or redirected")
        raw = path.read_bytes()
        if not raw or len(raw) > 48_000:
            raise ReworkInputError("Previous candidate file size invalid")
        rework_ledger.previous_reads.add(relative_path)
        return json.dumps({
            "path": relative_path, "sha256": hashlib.sha256(raw).hexdigest(),
            "content": raw.decode("utf-8"),
        }, ensure_ascii=False)

    return original_tools + [read_failure_evidence, read_previous_candidate]


def _bounded_log(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 100_000:
        raise ReworkInputError("Sandbox feedback log unavailable or oversized")
    return path.read_text(encoding="utf-8", errors="replace")[-_MAX_FEEDBACK:]


def evaluate_rework(
    *, report: EngineerReport, workspace: CandidateWorkspace,
    engineer_ledger: EngineerLedger, rework_ledger: ReworkLedger,
    architect_digest: str, previous_file_hashes: dict[str, str],
) -> tuple[dict, dict]:
    gate = evaluate_engineer(
        report, workspace, engineer_ledger,
        expected_architect_digest=architect_digest,
    )
    failures = list(gate.failures)
    if not rework_ledger.read_failure:
        failures.append("Engineer never read actual failing sandbox test evidence")
    if not {"solution.py", "pipeline.py"}.issubset(rework_ledger.previous_reads):
        failures.append("Engineer did not read prior solution.py and pipeline.py")
    current = {entry["path"]: entry["sha256"] for entry in gate.actual_written_files}
    if current and not any(
        current.get(name) != expected for name, expected in previous_file_hashes.items()
    ):
        failures.append("Rework produced identical candidate bytes; no actual correction")
    if not previous_file_hashes or not current:
        failures.append("Missing old or new candidate provenance")
    result = gate.model_dump(mode="json")
    result["failures"] = failures
    if failures:
        result["status"] = "INCOMPLETE"
    return result, {
        "previous_file_hashes": previous_file_hashes,
        "current_file_hashes": current,
        "previous_files_read": sorted(rework_ledger.previous_reads),
        "failure_evidence_read": rework_ledger.read_failure,
        "actual_change": previous_file_hashes != current,
    }


async def run_rework_foundry(
    *, spec: TaskSpec, architect: ArchitectReport,
    workspace: CandidateWorkspace, engineer_ledger: EngineerLedger,
    rework_ledger: ReworkLedger, prior_root: Path, verdict: dict,
    feedback_dir: Path, architect_digest: str, endpoint: str, model: str,
) -> str:
    from agent_framework import Agent
    from agent_framework.foundry import FoundryChatClient
    from azure.identity import DefaultAzureCredential

    client = FoundryChatClient(
        project_endpoint=endpoint, model=model,
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True),
    )
    settings = getattr(client, "function_invocation_configuration", None)
    if settings is not None:
        settings.update({
            "max_iterations": 40, "max_function_calls": 60,
            "max_duration_seconds": 700,
            "allow_concurrent_invocation": False,
        })
    agent = Agent(
        name="data_engineer_rework",
        client=client,
        instructions=(
            instructions("rebuild")
            + "\nTHIS IS ITERATION 2 AFTER A GENUINE P3 FAILURE. "
            "DO NOT pretend the previous candidate was accepted. "
            "First read_failure_evidence and read_previous_candidate for "
            "solution.py and pipeline.py (and earlier tests as needed), "
            "then read the original task, Architect contract, and input "
            "fixtures via the existing Engineer tools. The original error is "
            "REAL: reproduce it mentally and repair its root cause rather "
            "than changing tests. You must independently WRITE ALL required "
            "candidate files again, using real write_candidate_file calls. "
            "You cannot edit original employer tests or input data. "
            "Then show_diff and request_validation. The new code will be "
            "executed only later in a separate secret-free Docker job. "
            "When returning EngineerReport, use the EXACT accepted P1 "
            "architect_report_sha256 given in read_architect_contract "
            "and in this instruction: " + architect_digest + "."
        ),
        tools=rework_tools(
            spec=spec, architect=architect,
            workspace=workspace, engineer_ledger=engineer_ledger,
            rework_ledger=rework_ledger, prior_root=prior_root,
            verdict=verdict, feedback_dir=feedback_dir,
        ),
    )
    outcome = await agent.run(
        "Repair the genuinely failed P3 candidate. The previous test traceback "
        "is available from read_failure_evidence. Write a complete corrected "
        "candidate, not a prose proposal. P1 Architect SHA: " + architect_digest
    )
    return outcome.text or ""


def main() -> None:
    parser = argparse.ArgumentParser(description="P5 real Foundry rework round 2")
    parser.add_argument("--previous-engineer-dir", type=Path, required=True)
    parser.add_argument("--p3-dir", type=Path, required=True)
    parser.add_argument("--architect-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    spec = load_task_spec(
        repo_root=ROOT, encoded=os.getenv("CLOUDFIDE_TASK_SPEC_B64") or None,
    )
    architect, approved, inputs = verified_architect(args.architect_dir, spec, "rebuild")
    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    model = os.getenv("FOUNDRY_MODEL")
    if not endpoint or not model:
        raise SystemExit("Foundry deployment configuration missing")
    with tempfile.TemporaryDirectory(prefix="cloudfide-rework-") as temp:
        base = Path(temp)
        prior = base / "prior"
        outcome, _, admitted, prior_digest = verified_failed_candidate(
            previous_dir=args.previous_engineer_dir,
            p3_dir=args.p3_dir, stage=prior,
        )
        workspace = create_workspace(ROOT, base / "candidate", "rebuild")
        engineer_ledger, rework_ledger = EngineerLedger(), ReworkLedger()
        answer = asyncio.run(run_rework_foundry(
            spec=spec, architect=architect, workspace=workspace,
            engineer_ledger=engineer_ledger, rework_ledger=rework_ledger,
            prior_root=prior, verdict=outcome, feedback_dir=args.p3_dir,
            architect_digest=approved.report_sha256,
            endpoint=endpoint, model=model,
        ))
        from .input_manifest import verify_unchanged_inputs
        verify_unchanged_inputs(ROOT, inputs)
        try:
            report = EngineerReport.model_validate_json(answer.strip())
        except ValueError:
            raise SystemExit("Rework Engineer did not produce a valid report") from None
        previous_hashes = {entry["path"]: entry["sha256"] for entry in admitted["files"]}
        gate, lineage = evaluate_rework(
            report=report, workspace=workspace,
            engineer_ledger=engineer_ledger, rework_ledger=rework_ledger,
            architect_digest=approved.report_sha256,
            previous_file_hashes=previous_hashes,
        )
        lineage.update({
            "iteration": 2,
            "source_run_id": os.getenv("GITHUB_RUN_ID"),
            "previous_candidate_digest": prior_digest,
            "previous_p3_verdict_sha256": hashlib.sha256(
                (args.p3_dir / "verification.json").read_bytes()
            ).hexdigest(),
        })
        args.output_dir.mkdir(parents=True, exist_ok=True)
        _atomic_json(args.output_dir / "engineer_report.json", report.model_dump(mode="json"))
        _atomic_json(args.output_dir / "engineer_gate.json", gate)
        _atomic_json(args.output_dir / "rework_lineage.json", lineage)
        _atomic_json(
            args.output_dir / "validation_request.json",
            workspace.validation_requests[-1] if workspace.validation_requests
            else {"status": "NOT_REQUESTED"},
        )
        if workspace.validation_requests:
            _export_files(workspace, args.output_dir / "candidate_bundle.zip")
        print(json.dumps({
            "status": gate["status"], "iteration": 2,
            "failure_evidence_read": rework_ledger.read_failure,
            "previous_files_read": sorted(rework_ledger.previous_reads),
            "actual_files_written": len(workspace.writes),
            "errors": gate["failures"], "candidate_executed": False,
        }))
        if gate["status"] != "CANDIDATE_READY_FOR_SANDBOX":
            raise SystemExit(2)


if __name__ == "__main__":
    main()
