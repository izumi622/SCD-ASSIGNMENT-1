"""Failure-path tests prevent false evidence and accidental credential exposure."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

folder = Path(__file__).resolve().parents[2] / "scripts/evidence"
sys.path.insert(0, str(folder))


def module(name):
    spec = importlib.util.spec_from_file_location(name, folder / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_kubectl_failures_do_not_include_secret_payloads(monkeypatch):
    common = module("common")
    runner = Mock(return_value=SimpleNamespace(returncode=1, stdout="", stderr="private-password"))
    monkeypatch.setattr(common.subprocess, "run", runner)
    with pytest.raises(RuntimeError, match="kubectl operation failed") as error:
        common.kubectl("apply", "-f", "-", data="private-password")
    assert "private-password" not in str(error.value)
    assert runner.call_args.args[0][:3] == ["kubectl", "--context", "kind-civicpulse-evidence"]


def test_failed_load_preserves_results_and_stops(monkeypatch, tmp_path):
    measure = module("measure")
    monkeypatch.setattr(measure, "OUT", tmp_path)
    monkeypatch.setattr(measure, "apply", Mock())
    monkeypatch.setattr(measure, "sample", Mock())
    monkeypatch.setattr(measure, "get", lambda *a: {"status": {"failed": 1}})
    monkeypatch.setattr(measure, "kubectl", lambda *a: 'CIVICPULSE_SUMMARY={"metrics":{}}')
    saved = {}
    monkeypatch.setattr(measure, "save", lambda name, value: saved.update({name: value}))
    with pytest.raises(RuntimeError, match="did not pass"):
        measure.run_load("baseline")
    assert saved["baseline-result.json"]["job_succeeded"] is False
    assert (tmp_path / "baseline-k6.log").exists()


def test_rollback_restores_spec_when_failure_cannot_be_observed(monkeypatch):
    rollback = module("rollback")
    original = {
        "spec": {"template": {"spec": {"containers": [{"name": "backend", "image": "tested:sha"}]}}}
    }
    monkeypatch.setattr(
        rollback, "get", lambda kind, *a: original if kind == "deployment" else {"items": []}
    )
    monkeypatch.setattr(rollback, "kubectl", Mock())
    monkeypatch.setattr(rollback.time, "sleep", Mock())
    applied = Mock()
    monkeypatch.setattr(rollback, "apply", applied)
    saved = {}
    monkeypatch.setattr(rollback, "save", lambda name, value: saved.update({name: value}))
    with pytest.raises(RuntimeError, match="not observed"):
        rollback.main()
    assert applied.call_args.args[0]["spec"] == original["spec"]
    assert not saved["rollback.json"]["undo_ready"]


def test_report_marks_absent_results_missing(monkeypatch, tmp_path):
    report = module("report")
    monkeypatch.setattr(report, "OUT", tmp_path)
    monkeypatch.setattr(
        report, "save", lambda name, value: (tmp_path / name).write_text(json.dumps(value))
    )
    report.main()
    findings = json.loads((tmp_path / "findings.json").read_text())
    assert findings and not any(findings.values())
    assert "NOT demonstrated" in (tmp_path / "REPORT.md").read_text()
