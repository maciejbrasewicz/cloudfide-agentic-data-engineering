import json

import pytest
from pydantic import ValidationError

from contracts import DataPolicy


def test_default_policy_is_valid():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    DataPolicy.model_validate_json((root / "contracts" / "data_policy.json").read_text())


def test_unapproved_policy_is_rejected():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / "contracts" / "data_policy.json").read_text())
    policy["missing_unit_price"] = "use_product_average"
    with pytest.raises(ValidationError):
        DataPolicy.model_validate(policy)
    policy["missing_unit_price"] = "unique_price_per_product_or_fail"
    policy["execute_python"] = "print('surprise')"
    with pytest.raises(ValidationError):
        DataPolicy.model_validate(policy)
