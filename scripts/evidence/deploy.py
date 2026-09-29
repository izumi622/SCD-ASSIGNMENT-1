"""Deploy the tested source into the disposable Actions evidence cluster."""

import os
import secrets
import subprocess

from common import NAMESPACE, apply, kubectl, manifest, save, timestamp


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Run through Assignment Evidence in GitHub Actions")
    sha = os.environ["GITHUB_SHA"]
    backend = f"civicpulse-backend:{sha}"
    frontend = f"civicpulse-frontend:{sha}"
    manifest("namespace.yaml")
    password = secrets.token_hex(24)
    apply(
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "civicpulse-secrets", "namespace": NAMESPACE},
            "type": "Opaque",
            "stringData": {
                "POSTGRES_USER": "civicpulse",
                "POSTGRES_PASSWORD": password,
                "POSTGRES_DB": "civicpulse_db",
                "DATABASE_URL": f"postgresql+asyncpg://civicpulse:{password}@postgres-svc:5432/civicpulse_db",
                "SYNC_DATABASE_URL": f"postgresql://civicpulse:{password}@postgres-svc:5432/civicpulse_db",
                "REDIS_URL": "redis://redis-svc:6379/0",
                "GROQ_API_KEY": "",
            },
        }
    )
    for name in ("configmap.yaml", "postgres.yaml", "redis.yaml"):
        manifest(name)
    for target in ("statefulset/postgres", "deployment/redis"):
        kubectl("rollout", "status", target, "-n", NAMESPACE, "--timeout=300s")
    manifest("migration-job.yaml", backend=backend)
    kubectl("wait", "--for=condition=complete", "job/migrations", "-n", NAMESPACE, "--timeout=300s")
    # Migration logs contain only Alembic/seed output; omit environment manifests.
    save("migration.json", {"log": kubectl("logs", "job/migrations", "-n", NAMESPACE)})
    manifest("backend.yaml", backend=backend)
    manifest("frontend.yaml", frontend=frontend)
    for name in ("backend", "frontend"):
        kubectl("rollout", "status", f"deployment/{name}", "-n", NAMESPACE, "--timeout=300s")
    for name in ("hpa.yaml", "vpa.yaml", "pdb.yaml"):
        manifest(name)
    save(
        "provenance.json",
        {
            "commit": sha,
            "time_utc": timestamp(),
            "run_url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
            "backend_image": backend,
            "frontend_image": frontend,
            "provider": "simulated",
            "scope": "isolated CI cluster; synthetic read-only load",
            "kubectl_version": kubectl("version", "-o", "json"),
            "kind_version": subprocess.check_output(["kind", "version"], text=True).strip(),
        },
    )


if __name__ == "__main__":
    main()
