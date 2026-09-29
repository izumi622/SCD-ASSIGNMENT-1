"""Small kubectl adapter for an isolated, explicitly named evidence cluster."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CONTEXT = "kind-civicpulse-evidence"
NAMESPACE = "civicpulse"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evidence-output"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save(name, data):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def kubectl(*args, data=None):
    result = subprocess.run(
        ["kubectl", "--context", CONTEXT, *args],
        input=data,
        text=True,
        capture_output=True,
        check=False,
        timeout=360,
    )
    if result.returncode:
        # No raw manifests or Secret values in exception messages/artifacts.
        raise RuntimeError(f"kubectl operation failed: {args[0]}")
    return result.stdout


def get(kind, name=None):
    args = ["get", kind]
    if name:
        args.append(name)
    return json.loads(kubectl(*args, "-n", NAMESPACE, "-o", "json"))


def apply(obj):
    return kubectl("apply", "-f", "-", data=json.dumps(obj))


def manifest(filename, backend=None, frontend=None):
    text = (ROOT / "k8s" / "base" / filename).read_text()
    if backend:
        text = text.replace("ghcr.io/civicpulse/backend:IMAGE_TAG", backend)
    if frontend:
        text = text.replace("ghcr.io/civicpulse/frontend:IMAGE_TAG", frontend)
    kubectl("apply", "-f", "-", data=text)


def quantity(value):
    """Parse CPU and memory quantities emitted by Kubernetes/VPA."""
    import re
    from decimal import Decimal

    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)", str(value))
    if not match:
        raise ValueError(f"Unsupported resource quantity: {value}")
    multipliers = {
        "": 1,
        "n": Decimal("1e-9"),
        "u": Decimal("1e-6"),
        "m": Decimal("1e-3"),
        "k": 1000,
        "K": 1000,
        "M": 1000**2,
        "G": 1000**3,
        "T": 1000**4,
        "Ki": 1024,
        "Mi": 1024**2,
        "Gi": 1024**3,
        "Ti": 1024**4,
    }
    if match[2] not in multipliers:
        raise ValueError(f"Unsupported resource suffix: {match[2]}")
    return Decimal(match[1]) * multipliers[match[2]]


def bounded_requests(target, limits):
    result = {}
    for resource in ("cpu", "memory"):
        if quantity(target[resource]) <= 0:
            raise ValueError("VPA target must be positive")
        result[resource] = (
            target[resource]
            if quantity(target[resource]) <= quantity(limits[resource])
            else limits[resource]
        )
    return result
