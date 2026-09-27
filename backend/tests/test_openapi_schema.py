import re
from pathlib import Path

from app.main import app
from app.models.enums import Category, Priority, Status


def test_openapi_schema_matches_typescript_types():
    """Validates that TypeScript API types in frontend/src/api/types.ts
    accurately reflect the backend OpenAPI schema.
    """
    openapi = app.openapi()
    schemas = openapi.get("components", {}).get("schemas", {})

    # 1. Enums
    backend_categories = {c.value for c in Category}
    backend_priorities = {p.value for p in Priority}
    backend_statuses = {s.value for s in Status}

    types_file = (
        Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "api" / "types.ts"
    )
    assert types_file.exists(), f"types.ts not found at {types_file}"
    content = types_file.read_text(encoding="utf-8")

    # Extract Category from types.ts
    cat_match = re.search(r"export type Category = ([^;]+);", content)
    assert cat_match, "Category type not found in types.ts"
    frontend_categories = set(re.findall(r'"([^"]+)"', cat_match.group(1)))
    assert frontend_categories == backend_categories, (
        f"Category mismatch: frontend={frontend_categories} vs backend={backend_categories}"
    )

    # Extract Priority from types.ts
    pri_match = re.search(r"export type Priority = ([^;]+);", content)
    assert pri_match, "Priority type not found in types.ts"
    frontend_priorities = set(re.findall(r'"([^"]+)"', pri_match.group(1)))
    assert frontend_priorities == backend_priorities, (
        f"Priority mismatch: frontend={frontend_priorities} vs backend={backend_priorities}"
    )

    # Extract Status from types.ts
    stat_match = re.search(r"export type Status = ([^;]+);", content)
    assert stat_match, "Status type not found in types.ts"
    frontend_statuses = set(re.findall(r'"([^"]+)"', stat_match.group(1)))
    assert frontend_statuses == backend_statuses, (
        f"Status mismatch: frontend={frontend_statuses} vs backend={backend_statuses}"
    )

    # 2. Check Complaint fields
    complaint_schema = schemas.get("ComplaintResponse")
    assert complaint_schema, "ComplaintResponse schema missing in OpenAPI"
    required_complaint_props = set(complaint_schema.get("properties", {}).keys())

    # Verify key Complaint properties exist in frontend types.ts
    expected_props = [
        "id",
        "text",
        "location",
        "category",
        "priority",
        "status",
        "triaged_by",
        "triage_latency_ms",
        "created_at",
        "updated_at",
    ]
    for prop in expected_props:
        assert prop in required_complaint_props, f"Property {prop} missing from backend schema"
        assert f"{prop}:" in content or f"{prop}?:" in content, (
            f"Property {prop} missing from frontend types.ts"
        )

    # 3. Check ComplaintCreate fields
    create_schema = schemas.get("ComplaintCreate")
    assert create_schema, "ComplaintCreate schema missing in OpenAPI"
    create_props = set(create_schema.get("properties", {}).keys())
    for prop in ["text", "location"]:
        assert prop in create_props, f"{prop} missing from ComplaintCreate schema"
        assert f"{prop}: string" in content, (
            f"{prop}: string missing from ComplaintCreate interface"
        )
