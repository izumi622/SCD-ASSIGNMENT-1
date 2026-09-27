#!/usr/bin/env python3
"""
CivicPulse Submission Lint Tool
Checks that the repository contains all files required by the assignment rubric.
Run from the repository root: python scripts/check_submission.py
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_FILES = [
    # Documentation
    "README.md",
    "docs/AI-USAGE.md",
    "docs/RUNBOOK.md",
    "docs/ENGINEERING-NOTES.md",
    "docs/TRIAGE.md",
    "docs/adr/ADR-001-four-layer-architecture.md",
    "docs/adr/ADR-002-ai-triage-strategy.md",
    "docs/adr/ADR-003-caching-strategy.md",
    "docs/adr/ADR-004-pii-and-data-governance.md",
    # Backend
    "backend/Dockerfile",
    "backend/.dockerignore",
    "backend/requirements.txt",
    "backend/alembic.ini",
    "backend/alembic/versions/001_initial_schema.py",
    "backend/app/main.py",
    "backend/app/routes/complaints.py",
    "backend/app/routes/probes.py",
    "backend/app/services/complaint.py",
    "backend/app/repositories/complaint.py",
    "backend/app/providers/cache.py",
    "backend/app/providers/triage.py",
    "backend/app/models/db.py",
    "backend/app/models/schemas.py",
    "backend/app/models/enums.py",
    "backend/app/seed.py",
    "backend/tests/conftest.py",
    # Frontend
    "frontend/Dockerfile",
    "frontend/.dockerignore",
    "frontend/nginx.conf",
    "frontend/package.json",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "frontend/src/api/client.ts",
    "frontend/src/api/types.ts",
    # Docker Compose
    "docker-compose.yaml",
    "docker-compose.prod.yaml",
    ".env.example",
    ".gitignore",
    # Kubernetes
    "k8s/namespace.yaml",
    "k8s/secrets.yaml",
    "k8s/configmap.yaml",
    "k8s/postgres.yaml",
    "k8s/redis.yaml",
    "k8s/backend.yaml",
    "k8s/frontend.yaml",
    "k8s/ingress.yaml",
    "k8s/hpa.yaml",
    "k8s/vpa.yaml",
    "k8s/pdb.yaml",
    "k8s/migration-job.yaml",
    # CI/CD
    ".github/workflows/ci.yaml",
    ".github/workflows/cd.yaml",
]

REQUIRED_DIRS = [
    "backend/app/routes",
    "backend/app/services",
    "backend/app/repositories",
    "backend/app/providers",
    "backend/app/models",
    "backend/tests",
    "frontend/src/pages",
    "frontend/src/components",
    "frontend/src/hooks",
    "frontend/src/api",
    "k8s",
    "docs/adr",
    ".github/workflows",
]


def check():
    errors = []
    warnings = []

    print("=" * 60)
    print("  CivicPulse Submission Lint")
    print("=" * 60)
    print()

    # Check required files
    print("📄 Checking required files...")
    for f in REQUIRED_FILES:
        path = os.path.join(ROOT, f)
        if os.path.isfile(path):
            print(f"  ✅ {f}")
        else:
            print(f"  ❌ {f}")
            errors.append(f"Missing file: {f}")

    print()

    # Check required directories
    print("📁 Checking required directories...")
    for d in REQUIRED_DIRS:
        path = os.path.join(ROOT, d)
        if os.path.isdir(path):
            print(f"  ✅ {d}/")
        else:
            print(f"  ❌ {d}/")
            errors.append(f"Missing directory: {d}")

    print()

    # Check .env is NOT committed
    env_path = os.path.join(ROOT, ".env")
    if os.path.isfile(env_path):
        warnings.append(".env file exists — make sure it's in .gitignore and not committed!")

    # Check .gitignore contains .env
    gitignore_path = os.path.join(ROOT, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path) as f:
            content = f.read()
        if ".env" not in content:
            warnings.append(".gitignore does not contain '.env' — secrets may be committed!")

    # Check backend tests exist
    tests_dir = os.path.join(ROOT, "backend", "tests")
    if os.path.isdir(tests_dir):
        test_files = [f for f in os.listdir(tests_dir) if f.startswith("test_") and f.endswith(".py")]
        count = len(test_files)
        if count < 14:
            warnings.append(f"Only {count} test files found in backend/tests/ (target: ≥ 14)")
        else:
            print(f"🧪 Found {count} test files (target: ≥ 14)")

    # Summary
    print()
    print("=" * 60)
    if warnings:
        print(f"⚠️  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"   ⚠️  {w}")

    if errors:
        print(f"❌ {len(errors)} error(s):")
        for e in errors:
            print(f"   ❌ {e}")
        print()
        print("RESULT: FAIL")
        return 1
    else:
        print("✅ All required files and directories present!")
        print()
        print("RESULT: PASS")
        return 0


if __name__ == "__main__":
    sys.exit(check())
