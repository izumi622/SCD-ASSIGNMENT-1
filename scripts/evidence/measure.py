"""Collect real HPA samples and k6 results; never manufacture scaling observations."""

import json
import time

from common import NAMESPACE, OUT, ROOT, apply, get, kubectl, save, timestamp


def sample(phase):
    hpas = get("hpa")["items"]
    pods = get("pods")["items"]
    record = {"time_utc": timestamp(), "phase": phase, "hpas": []}
    for hpa in hpas:
        app = hpa["spec"]["scaleTargetRef"]["name"]
        selected = [
            p
            for p in pods
            if p.get("metadata", {}).get("labels", {}).get("app") == app
            and not p["metadata"].get("deletionTimestamp")
        ]
        record["hpas"].append(
            {
                "name": hpa["metadata"]["name"],
                "current": hpa.get("status", {}).get("currentReplicas", 0),
                "desired": hpa.get("status", {}).get("desiredReplicas", 0),
                "ready": sum(
                    any(
                        c.get("type") == "Ready" and c.get("status") == "True"
                        for c in p.get("status", {}).get("conditions", [])
                    )
                    for p in selected
                ),
                "metrics": hpa.get("status", {}).get("currentMetrics", []),
                "conditions": hpa.get("status", {}).get("conditions", []),
            }
        )
    OUT.mkdir(exist_ok=True)
    with (OUT / "hpa-samples.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
    return record


def run_load(phase):
    name = f"evidence-load-{phase}"
    apply(
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "evidence-load", "namespace": NAMESPACE},
            "data": {"test.js": (ROOT / "load/evidence.js").read_text()},
        }
    )
    apply(
        {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {"name": name, "namespace": NAMESPACE},
            "spec": {
                "backoffLimit": 0,
                "activeDeadlineSeconds": 600,
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "k6",
                                "image": "grafana/k6:1.0.0",
                                "args": ["run", "--quiet", "/scripts/test.js"],
                                "env": [{"name": "TARGET_URL", "value": "http://frontend-svc"}],
                                "resources": {
                                    "requests": {"cpu": "100m", "memory": "128Mi"},
                                    "limits": {"cpu": "1000m", "memory": "512Mi"},
                                },
                                "volumeMounts": [
                                    {"name": "script", "mountPath": "/scripts", "readOnly": True}
                                ],
                            }
                        ],
                        "volumes": [{"name": "script", "configMap": {"name": "evidence-load"}}],
                    }
                },
            },
        }
    )
    completed = False
    for _ in range(65):
        sample(phase)
        status = get("job", name).get("status", {})
        if status.get("succeeded") or status.get("failed"):
            completed = bool(status.get("succeeded"))
            break
        time.sleep(10)
    log = kubectl("logs", f"job/{name}", "-n", NAMESPACE)
    (OUT / f"{phase}-k6.log").write_text(log, encoding="utf-8")
    summary = None
    for line in log.splitlines():
        if line.startswith("CIVICPULSE_SUMMARY="):
            summary = json.loads(line.split("=", 1)[1])
    save(f"{phase}-result.json", {"job_succeeded": completed, "summary": summary})
    if not completed or summary is None:
        raise RuntimeError(f"{phase} load did not pass; inspect saved evidence")
    # Observe downscaling without changing the configured stabilization policy.
    for _ in range(36):
        sample(phase + "-cooldown")
        time.sleep(10)


def main():
    # Metrics must actually be available before a scaling experiment begins.
    for attempt in range(24):
        hpas = get("hpa")["items"]
        if hpas and all(h.get("status", {}).get("currentMetrics") for h in hpas):
            break
        if attempt == 23:
            raise RuntimeError("HPA metrics did not become available")
        time.sleep(10)
    save(
        "baseline-deployments.json",
        {name: get("deployment", name)["spec"] for name in ("backend", "frontend")},
    )
    run_load("baseline")


if __name__ == "__main__":
    main()
