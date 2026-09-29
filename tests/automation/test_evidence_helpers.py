import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "common", Path(__file__).resolve().parents[2] / "scripts/evidence/common.py"
)
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


@pytest.mark.parametrize(
    "left,right", [("500m", "0.5"), ("1Gi", "1024Mi"), ("1e3", "1k"), ("1000000n", "1m")]
)
def test_quantity_equivalence(left, right):
    assert common.quantity(left) == common.quantity(right)


def test_request_target_capped_to_existing_limit():
    assert common.bounded_requests(
        {"cpu": "2", "memory": "128Mi"}, {"cpu": "500m", "memory": "512Mi"}
    ) == {"cpu": "500m", "memory": "128Mi"}


@pytest.mark.parametrize("value", ["garbage", "1watts", ""])
def test_invalid_quantity_rejected(value):
    with pytest.raises(ValueError):
        common.quantity(value)


def test_zero_request_rejected():
    with pytest.raises(ValueError):
        common.bounded_requests({"cpu": "0", "memory": "128Mi"}, {"cpu": "1", "memory": "512Mi"})
