"""Test governance rules for sg-engine."""

from __future__ import annotations

import json
from pathlib import Path


def test_no_pii_fields_in_schemas():
    """Verify no PII fields appear in schema required properties."""
    forbidden = ["player_id", "account_id", "email", "phone", "user_id"]

    schemas_dir = Path(__file__).parent.parent / "src" / "sg_engine" / "schemas"
    for schema_path in schemas_dir.glob("*.json"):
        content = schema_path.read_text()
        data = json.loads(content)

        # Check required fields at root
        required = data.get("required", [])
        for field in forbidden:
            assert field not in required, f"PII field {field} in {schema_path.name}"

        # Check properties
        props = data.get("properties", {})
        for field in forbidden:
            if field in props:
                # Only OK if wrapped in "not" block
                assert False, f"PII field {field} exposed in {schema_path.name}"


def test_schemas_valid_json():
    """Verify all schema files are valid JSON."""
    schemas_dir = Path(__file__).parent.parent / "src" / "sg_engine" / "schemas"
    for schema_path in schemas_dir.glob("*.json"):
        content = schema_path.read_text()
        data = json.loads(content)  # Will raise if invalid
        assert "$schema" in data or "type" in data, f"Invalid schema: {schema_path.name}"
