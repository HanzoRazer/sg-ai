# src/sg_engine/validate.py
"""
Strict JSON Schema validation helpers.

Policy:
- Fail fast.
- No "best effort" coercion.
- No silent fallback behavior.
"""

from __future__ import annotations

from typing import Any, Dict

from jsonschema import Draft202012Validator


class SchemaValidationError(ValueError):
    pass


def validate_json_schema(data: Any, schema: Dict[str, Any]) -> None:
    """
    Validate `data` against a Draft 2020-12 JSON schema dict.

    Raises:
      SchemaValidationError on first validation failure.
    """
    if not isinstance(schema, dict) or not schema:
        raise SchemaValidationError("Schema must be a non-empty dict")

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if errors:
        e0 = errors[0]
        path = "$"
        if e0.path:
            path += "".join([f"[{repr(p)}]" if isinstance(p, int) else f".{p}" for p in e0.path])
        msg = f"{path}: {e0.message}"
        raise SchemaValidationError(msg)
