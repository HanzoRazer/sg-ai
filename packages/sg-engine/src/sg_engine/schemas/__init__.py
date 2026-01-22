# src/sg_engine/schemas/__init__.py
"""
Schema loader utilities.

Design goals:
- Load bundled JSON schemas from this package.
- Fail loudly if missing.
- No network access, no registry lookups.

Schema filenames live alongside this module:
- coach_context_packet_v1.json
- coaching_draft_v1.json
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, Dict


class SchemaNotFoundError(FileNotFoundError):
    pass


def load_schema(filename: str) -> Dict[str, Any]:
    """
    Load a JSON schema file bundled in sg_engine.schemas.

    Args:
      filename: e.g. "coach_context_packet_v1.json"

    Returns:
      schema dict

    Raises:
      SchemaNotFoundError if missing
      ValueError if JSON is invalid
    """
    try:
        p = files(__package__).joinpath(filename)
        if not p.is_file():
            raise SchemaNotFoundError(f"Schema file not found: {filename}")
        raw = p.read_text(encoding="utf-8")
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError(f"Schema must be a JSON object dict: {filename}")
        return obj
    except SchemaNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to load schema {filename}: {e}") from e
