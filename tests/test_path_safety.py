"""ETL outputs must not overwrite original input data or approved policy."""
from pathlib import Path

import pytest

from pipeline import ROOT, DataQualityError, run_pipeline


@pytest.mark.parametrize("collision", ["source", "policy", "report"])
def test_artifact_collisions_are_rejected_before_writing(tmp_path: Path, collision: str):
    source = tmp_path / "source.csv"
    source.write_bytes((ROOT / "sales.csv").read_bytes())
    policy = tmp_path / "policy.json"
    policy.write_bytes((ROOT / "contracts/data_policy.json").read_bytes())
    output = tmp_path / "regions.csv"
    report = tmp_path / "audit.json"

    if collision == "source":
        output = source
    elif collision == "policy":
        report = policy
    elif collision == "report":
        report = output

    source_before, policy_before = source.read_bytes(), policy.read_bytes()
    with pytest.raises(DataQualityError, match="must be distinct"):
        run_pipeline(source, output, report, policy)

    assert source.read_bytes() == source_before
    assert policy.read_bytes() == policy_before
    if collision != "source":
        assert not output.exists()
