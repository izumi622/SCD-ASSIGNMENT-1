"""Exercise a failed rollout and both imperative/declarative restoration in CI only."""

import copy
import json
import time

from common import NAMESPACE, apply, get, kubectl, save, timestamp


def readiness():
    result = kubectl(
        "exec",
        "deployment/backend",
        "-n",
        NAMESPACE,
        "--",
        "python",
        "-c",
        "import urllib.request; print(urllib.request.urlopen('http://frontend-svc/ready', timeout=10).read().decode())",
    )
    if json.loads(result).get("status") != "ready":
        raise RuntimeError("Readiness did not pass after rollback")


def main():
    original = get("deployment", "backend")
    original_spec = copy.deepcopy(original["spec"])
    original_image = next(
        c["image"]
        for c in original_spec["template"]["spec"]["containers"]
        if c["name"] == "backend"
    )
    restoration = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "backend", "namespace": NAMESPACE},
        "spec": original_spec,
    }
    report = {
        "started": timestamp(),
        "original_image": original_image,
        "failed_rollout_observed": False,
        "undo_ready": False,
        "declarative_ready": False,
    }
    bad_image = "civicpulse-backend:deliberately-missing-evidence"
    try:
        kubectl(
            "patch",
            "deployment",
            "backend",
            "-n",
            NAMESPACE,
            "--type=strategic",
            "-p",
            json.dumps(
                {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "backend",
                                        "image": bad_image,
                                        "imagePullPolicy": "Never",
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
        )
        for _ in range(24):
            pods = get("pods")["items"]
            bad = [
                p for p in pods if any(c.get("image") == bad_image for c in p["spec"]["containers"])
            ]
            if any(
                s.get("state", {}).get("waiting", {}).get("reason") == "ErrImageNeverPull"
                for p in bad
                for s in p.get("status", {}).get("containerStatuses", [])
            ):
                report["failed_rollout_observed"] = True
                break
            time.sleep(5)
        save("rollback-failure-pods.json", get("pods"))
        if not report["failed_rollout_observed"]:
            raise RuntimeError("Expected failed rollout was not observed")
        kubectl("rollout", "undo", "deployment/backend", "-n", NAMESPACE)
        kubectl("rollout", "status", "deployment/backend", "-n", NAMESPACE, "--timeout=300s")
        readiness()
        report["undo_ready"] = True
        # Reproduce the bad rollout, then restore from the captured declarative specification.
        kubectl("set", "image", "deployment/backend", f"backend={bad_image}", "-n", NAMESPACE)
        apply(restoration)
        kubectl("rollout", "status", "deployment/backend", "-n", NAMESPACE, "--timeout=300s")
        readiness()
        restored = get("deployment", "backend")
        assert (
            next(
                c["image"]
                for c in restored["spec"]["template"]["spec"]["containers"]
                if c["name"] == "backend"
            )
            == original_image
        )
        report["declarative_ready"] = True
    finally:
        apply(restoration)
        report["finished"] = timestamp()
        save("rollback.json", report)


if __name__ == "__main__":
    main()
