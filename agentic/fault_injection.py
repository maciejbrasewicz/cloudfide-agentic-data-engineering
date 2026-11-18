"""Bounded, isolated fault injection for the *deterministic* engineering gate.

This is NOT an AI agent evaluation. It measures whether the data/quality gates
detect known faults. Agent sensitivity requires separate Foundry evaluations.
No mutated code or source data is ever written to the checked-out repository.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pipeline import ROOT

_ALLOWED_FILES = (
    "solution.py", "pipeline.py", "contracts.py",
    "sales.csv", "revenue_by_region.csv",
    "contracts/data_policy.json", "reports/data_quality.json",
    "tests/test_raw_oracle.py", "tests/test_path_safety.py",
)
_PYTHON = sys.executable
_GATE_TIMEOUT = 40


@dataclass(frozen=True)
class Challenge:
    id: str
    kind: Literal["code_mutant", "source_anomaly"]
    description: str
    expected_gate: str
    expected_signal: str
    target: str
    original: str | None = None
    replacement: str | None = None


CHALLENGES = (
    Challenge(
        id="FI-001",
        kind="code_mutant",
        description="Invert the sign of the line discount in the revenue expression",
        expected_gate="independent_decimal_oracle",
        expected_signal="FAILED tests/test_raw_oracle.py",
        target="pipeline.py",
        original='"quantity * unit_price - discount", "revenue"',
        replacement='"quantity * unit_price + discount", "revenue"',
    ),
    Challenge(
        id="FI-002",
        kind="code_mutant",
        description="Silently bypass source-exact deduplication",
        expected_gate="independent_decimal_oracle",
        expected_signal="FAILED tests/test_raw_oracle.py",
        target="pipeline.py",
        original="transactions = transactions.drop(index=raw_duplicate_indices).copy()",
        replacement="transactions = transactions.copy()",
    ),
    Challenge(
        id="FI-003",
        kind="code_mutant",
        description="Corrupt approved five-region normalization to lowercase labels",
        expected_gate="schema_and_region_guard",
        expected_signal="Unknown region",
        target="pipeline.py",
        original='transactions["region"] = transactions.region.str.strip().str.title()',
        replacement='transactions["region"] = transactions.region.str.strip().str.lower()',
    ),
    Challenge(
        id="FI-004",
        kind="code_mutant",
        description="Remove the output-to-input artifact collision guard",
        expected_gate="path_safety_regression",
        expected_signal="FAILED tests/test_path_safety.py",
        target="pipeline.py",
        original="if len(paths) != len(set(paths)):",
        replacement="if False:",
    ),
    Challenge(
        id="FI-005",
        kind="source_anomaly",
        description="Tamper with the source TOTAL quantity without changing order rows",
        expected_gate="raw_source_control",
        expected_signal="Raw source TOTAL mismatch",
        target="sales.csv",
    ),
)


class EvaluationError(RuntimeError):
    """The harness could not construct or evaluate a valid challenge."""


def _stage(destination: Path, root: Path) -> None:
    for name in _ALLOWED_FILES:
        source = root / name
        if not source.is_file():
            raise EvaluationError(f"Missing required source fixture: {name}")
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)


def _run(destination: Path, *arguments: str) -> dict:
    started = time.perf_counter_ns()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(destination)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run(
            [_PYTHON, *arguments], cwd=destination, env=env,
            capture_output=True, text=True, timeout=_GATE_TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise EvaluationError(f"Gate timed out after {_GATE_TIMEOUT}s: {arguments}") from exc
    return {
        "returncode": proc.returncode,
        "duration_ms": round((time.perf_counter_ns() - started) / 1_000_000, 3),
        # Log content deliberately is not carried into the public result.
        "_combined_output": proc.stdout[-12000:] + "\n" + proc.stderr[-12000:],
    }


def _tamper_total(csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
        columns = list(rows[0]) if rows else []
    totals = [row for row in rows if row["Order ID"] == "TOTAL"]
    if len(totals) != 1 or not totals[0]["Quantity "].isdigit():
        raise EvaluationError("Unexpected source TOTAL fixture")
    totals[0]["Quantity "] = str(int(totals[0]["Quantity "]) + 1)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _inject(challenge: Challenge, destination: Path) -> None:
    target = destination / challenge.target
    if challenge.kind == "source_anomaly":
        if challenge.id != "FI-005":
            raise EvaluationError("Unapproved source anomaly")
        _tamper_total(target)
        return
    if not challenge.original or not challenge.replacement:
        raise EvaluationError("Incomplete code mutation contract")
    text = target.read_text(encoding="utf-8")
    if text.count(challenge.original) != 1:
        raise EvaluationError(f"Mutation anchor drift in {challenge.id}")
    target.write_text(text.replace(challenge.original, challenge.replacement, 1), encoding="utf-8")


def _gate(challenge: Challenge, destination: Path) -> dict:
    if challenge.expected_gate == "path_safety_regression":
        return _run(destination, "-m", "pytest", "tests/test_path_safety.py", "-q")
    # For arithmetic mutants, generate the mutated output before comparing to the
    # separate raw-CSV Decimal oracle that does not call production functions.
    run = _run(destination, "pipeline.py")
    if challenge.expected_gate == "independent_decimal_oracle" and run["returncode"] == 0:
        return _run(destination, "-m", "pytest", "tests/test_raw_oracle.py", "-q")
    return run


def _measure_baseline(destination: Path) -> None:
    original = _run(destination, "pipeline.py")
    if original["returncode"] != 0:
        raise EvaluationError("Baseline pipeline failed before mutation")
    tests = _run(destination, "-m", "pytest", "tests/test_raw_oracle.py", "tests/test_path_safety.py", "-q")
    if tests["returncode"] != 0:
        raise EvaluationError("Baseline oracle or path-safety test failed")


def evaluate(root: Path = ROOT) -> dict:
    source_hash = hashlib.sha256((root / "sales.csv").read_bytes()).hexdigest()
    cases: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="cloudfide-mutation-lab-") as sandbox:
        temp_root = Path(sandbox)
        _stage(temp_root / "baseline", root)
        _measure_baseline(temp_root / "baseline")
        for challenge in CHALLENGES:
            destination = temp_root / challenge.id
            _stage(destination, root)
            _inject(challenge, destination)
            observed = _gate(challenge, destination)
            output = observed.pop("_combined_output")
            detected = observed["returncode"] != 0 and challenge.expected_signal in output
            cases.append({
                "id": challenge.id,
                "kind": challenge.kind,
                "description": challenge.description,
                "expected_gate": challenge.expected_gate,
                "detected": detected,
                "returncode": observed["returncode"],
                "duration_ms": observed["duration_ms"],
                "expected_signal_present": challenge.expected_signal in output,
            })
    mutant_cases = [case for case in cases if case["kind"] == "code_mutant"]
    anomaly_cases = [case for case in cases if case["kind"] == "source_anomaly"]
    return {
        "schema_version": 1,
        "framework": "isolated_deterministic_fault_injection",
        "scope": "quality_gate_detection_not_agent_accuracy",
        "source_sha256": source_hash,
        "cases": cases,
        "code_mutants_caught": sum(case["detected"] for case in mutant_cases),
        "code_mutants_total": len(mutant_cases),
        "source_anomalies_rejected": sum(case["detected"] for case in anomaly_cases),
        "source_anomalies_total": len(anomaly_cases),
        "no_original_files_modified": (
            hashlib.sha256((root / "sales.csv").read_bytes()).hexdigest() == source_hash
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely inject controlled defects into sandboxed ETL copies")
    parser.add_argument("--output", type=Path, default=ROOT / "fault_injection_runtime.json")
    args = parser.parse_args()
    report = evaluate()
    if not report["no_original_files_modified"]:
        raise EvaluationError("Original source hash changed during evaluation")
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if (
        report["code_mutants_caught"] != report["code_mutants_total"]
        or report["source_anomalies_rejected"] != report["source_anomalies_total"]
    ):
        raise SystemExit("Fault-injection quality gate failed")


if __name__ == "__main__":
    main()
