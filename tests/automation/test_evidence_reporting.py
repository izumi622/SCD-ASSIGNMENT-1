import importlib.util
import sys
from pathlib import Path

folder = Path(__file__).resolve().parents[2] / "scripts/evidence"
sys.path.insert(0, str(folder))
spec = importlib.util.spec_from_file_location("report", folder / "report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def sample(current, ready):
    return {
        "phase": "baseline",
        "hpas": [{"name": "backend-hpa", "current": current, "ready": ready}],
    }


def test_desired_or_unready_replicas_do_not_prove_scaling():
    assert not report.scaling_observed([sample(2, 2), sample(4, 2)], "baseline")


def test_actual_ready_scale_up_is_observed():
    assert report.scaling_observed([sample(2, 2), sample(4, 4)], "baseline")


def test_missing_samples_are_not_success():
    assert not report.scaling_observed([], "baseline")
