"""P3 independent financial oracle: never import the candidate under test."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pipeline import ROOT
from agentic.p3_oracle import (
    SandboxValidationError, compare_output, expected_revenues, validate_runner,
)


def test_reference_oracle_matches_original_cloudfide_output():
    totals, counts = expected_revenues(ROOT / "sales.csv")
    assert counts == {
        "raw_rows": 1507, "raw_transactions": 1505,
        "unique_transactions": 1500, "duplicate_extras": 5,
    }
    assert sum(totals.values()).__str__() == "2570247.03"
    result = compare_output(ROOT / "sales.csv", ROOT / "revenue_by_region.csv")
    assert result["reconciliation"] == "passed"
    assert result["net_revenue"] == "2570247.03"


def test_oracle_is_independent_of_candidate_and_production_code():
    source = (ROOT / "agentic/p3_oracle.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not {"solution", "pipeline", "dataframe_contracts", "agentic.workspace"} & modules
    assert "exec(" not in source
    assert "eval(" not in source


def test_wrong_region_total_rejected(tmp_path: Path):
    data = (ROOT / "revenue_by_region.csv").read_text(encoding="utf-8")
    bad = tmp_path / "bad.csv"
    bad.write_text(data.replace("Central,515824.67", "Central,515824.68"), encoding="utf-8")
    with pytest.raises(SandboxValidationError, match="reconciliation failed"):
        compare_output(ROOT / "sales.csv", bad)


def test_missing_region_and_bad_precision_rejected(tmp_path: Path):
    lines = (ROOT / "revenue_by_region.csv").read_text(encoding="utf-8").splitlines()
    output = tmp_path / "regions.csv"
    output.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(SandboxValidationError, match="five"):
        compare_output(ROOT / "sales.csv", output)
    output.write_text("\n".join(lines).replace("515824.67", "515824.670") + "\n", encoding="utf-8")
    with pytest.raises(SandboxValidationError, match="Malformed"):
        compare_output(ROOT / "sales.csv", output)


def test_sandbox_test_failure_cannot_be_overridden_by_matching_output(tmp_path: Path):
    (tmp_path / "test_exit_code.txt").write_text("1", encoding="utf-8")
    (tmp_path / "pipeline_exit_code.txt").write_text("0", encoding="utf-8")
    (tmp_path / "revenue_by_region.csv").write_bytes((ROOT / "revenue_by_region.csv").read_bytes())
    receipt = validate_runner(ROOT / "sales.csv", tmp_path)
    assert receipt["status"] == "FAILED"
    assert receipt["sandbox_test_exit_code"] == 1


def test_sandbox_success_requires_independent_reconciliation(tmp_path: Path):
    (tmp_path / "test_exit_code.txt").write_text("0", encoding="utf-8")
    (tmp_path / "pipeline_exit_code.txt").write_text("0", encoding="utf-8")
    (tmp_path / "revenue_by_region.csv").write_bytes((ROOT / "revenue_by_region.csv").read_bytes())
    receipt = validate_runner(ROOT / "sales.csv", tmp_path)
    assert receipt["status"] == "PASSED"
    assert receipt["net_revenue"] == "2570247.03"
