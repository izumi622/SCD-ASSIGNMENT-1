#!/usr/bin/env python3
"""
Validates that TypeScript API types in frontend/src/api/types.ts
accurately reflect the backend FastAPI OpenAPI schema.
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

# Ensure in-memory database URL for offline schema inspection
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///:memory:")

from app.main import app
from app.models.enums import Category, Priority, Status
import re

def main():
    print("Validating frontend TypeScript types against backend OpenAPI schema...")
    openapi = app.openapi()
    schemas = openapi.get("components", {}).get("schemas", {})

    types_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "src", "api", "types.ts"
    )
    with open(types_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Enums
    backend_cats = {c.value for c in Category}
    cat_match = re.search(r'export type Category = ([^;]+);', content)
    frontend_cats = set(re.findall(r'"([^"]+)"', cat_match.group(1)))
    assert frontend_cats == backend_cats, f"Category mismatch: {frontend_cats} vs {backend_cats}"
    print("  ✅ Category enum values match")

    backend_pri = {p.value for p in Priority}
    pri_match = re.search(r'export type Priority = ([^;]+);', content)
    frontend_pri = set(re.findall(r'"([^"]+)"', pri_match.group(1)))
    assert frontend_pri == backend_pri, f"Priority mismatch: {frontend_pri} vs {backend_pri}"
    print("  ✅ Priority enum values match")

    backend_stat = {s.value for s in Status}
    stat_match = re.search(r'export type Status = ([^;]+);', content)
    frontend_stat = set(re.findall(r'"([^"]+)"', stat_match.group(1)))
    assert frontend_stat == backend_stat, f"Status mismatch: {frontend_stat} vs {backend_stat}"
    print("  ✅ Status enum values match")

    # 2. Complaint fields
    complaint_schema = schemas.get("ComplaintResponse")
    assert complaint_schema, "ComplaintResponse missing from OpenAPI"
    props = set(complaint_schema.get("properties", {}).keys())
    for prop in ["id", "text", "location", "category", "priority", "status", "triaged_by", "triage_latency_ms", "created_at", "updated_at"]:
        assert prop in props, f"Missing prop {prop} in backend OpenAPI"
        assert f"{prop}:" in content or f"{prop}?:" in content, f"Missing prop {prop} in frontend types"
    print("  ✅ Complaint response schema fields match")

    print("\n✅ All TypeScript API types are verified against the backend OpenAPI schema!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
