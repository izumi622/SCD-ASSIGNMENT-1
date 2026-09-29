"""Record actual VPA targets, apply bounded requests, repeat the same workload."""

import time

from common import NAMESPACE, bounded_requests, get, kubectl, save
from measure import run_load


def main():
    recommendations = {}
    for attempt in range(40):
        for name in ("backend", "frontend"):
            obj = get("vpa", f"{name}-vpa")
            if obj["spec"]["updatePolicy"]["updateMode"] != "Off":
                raise RuntimeError("VPA must stay in recommendation-only mode")
            records = (
                obj.get("status", {}).get("recommendation", {}).get("containerRecommendations", [])
            )
            match = next((r for r in records if r["containerName"] == name), None)
            if match:
                recommendations[name] = match
        if len(recommendations) == 2:
            break
        if attempt == 39:
            save("vpa-recommendations.json", recommendations)
            raise RuntimeError("VPA recommendations incomplete; no fabricated targets were applied")
        time.sleep(15)
    save("vpa-recommendations.json", recommendations)
    changes = {}
    patches = []
    for name, recommendation in recommendations.items():
        spec = get("deployment", name)["spec"]
        container = next(c for c in spec["template"]["spec"]["containers"] if c["name"] == name)
        requests = bounded_requests(recommendation["target"], container["resources"]["limits"])
        changes[name] = {
            "before": container["resources"]["requests"],
            "recommended": recommendation["target"],
            "applied": requests,
            "limits": container["resources"]["limits"],
        }
        patch = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": name, "namespace": NAMESPACE},
            "spec": {
                "template": {
                    "spec": {"containers": [{"name": name, "resources": {"requests": requests}}]}
                }
            },
        }
        patches.append(patch)
        # Strategic merge changes only these named containers' requests.
        import json

        kubectl(
            "patch",
            "deployment",
            name,
            "-n",
            NAMESPACE,
            "--type=strategic",
            "-p",
            json.dumps(patch),
        )
    save("resource-changes.json", changes)
    # A real candidate overlay patch; review before adopting in the repository.
    save("measured-resource-patches.json", {"apiVersion": "v1", "kind": "List", "items": patches})
    for name in changes:
        kubectl("rollout", "status", f"deployment/{name}", "-n", NAMESPACE, "--timeout=300s")
    # Let new pods contribute usable metrics before repeating the workload.
    time.sleep(60)
    run_load("adjusted")


if __name__ == "__main__":
    main()
