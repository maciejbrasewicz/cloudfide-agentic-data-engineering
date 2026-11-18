"""Unit-level controls for deterministic, allowlisted fault injection.

The full five-case evaluation runs as a separate GitHub Actions job.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic.fault_injection import (
    CHALLENGES,
    EvaluationError,
    _inject,
    _stage,
)
from pipeline import ROOT


def test_challenges_are_bounded_and_unique():
    assert len(CHALLENGES) == 5
    assert len({case.id for case in CHALLENGES}) == len(CHALLENGES)
    assert sum(case.kind == "code_mutant" for case in CHALLENGES) == 4
    assert sum(case.kind == "source_anomaly" for case in CHALLENGES) == 1
    assert all(case.target in {"pipeline.py", "sales.csv"} for case in CHALLENGES)


@pytest.mark.parametrize("case", CHALLENGES, ids=lambda case: case.id)
def test_injection_affects_only_an_isolated_copy(tmp_path: Path, case):
    source_before = (ROOT / "sales.csv").read_bytes()
    pipeline_before = (ROOT / "pipeline.py").read_bytes()
    _stage(tmp_path, ROOT)
    _inject(case, tmp_path)
    target = tmp_path / case.target
    assert target.read_bytes() != (ROOT / case.target).read_bytes()
    assert (ROOT / "sales.csv").read_bytes() == source_before
    assert (ROOT / "pipeline.py").read_bytes() == pipeline_before


def test_injection_refuses_anchor_drift(tmp_path: Path):
    case = next(item for item in CHALLENGES if item.kind == "code_mutant")
    _stage(tmp_path, ROOT)
    target = tmp_path / case.target
    target.write_text("class Empty: pass\n", encoding="utf-8")
    with pytest.raises(EvaluationError, match="anchor drift"):
        _inject(case, tmp_path)
