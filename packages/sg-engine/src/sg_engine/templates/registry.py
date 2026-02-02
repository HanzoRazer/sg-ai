# src/sg_engine/templates/registry.py
"""
Template registry for sg-ai.

Design goals:
- Templates are versioned and immutable once published.
- Templates define expected behavior for coaching jobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any, List


class TemplateSpec:
    """Template specification."""

    def __init__(
        self,
        id: str,
        version: str,
        kind: str,
        description: str,
    ):
        self.id = id
        self.version = version
        self.kind = kind
        self.description = description


@dataclass(frozen=True)
class TemplateKey:
    id: str
    version: str


# Registry maps (template_id, template_version) to a TemplateSpec
_TEMPLATES: Dict[TemplateKey, TemplateSpec] = {}


def register_template(template_id: str, template_version: str, kind: str, description: str) -> None:
    """Register a template."""
    key = TemplateKey(template_id, template_version)
    if key in _TEMPLATES:
        raise RuntimeError(f"Duplicate template registration: {template_id}@{template_version}")
    _TEMPLATES[key] = TemplateSpec(template_id, template_version, kind, description)


def get_template(template_id: str, template_version: str) -> TemplateSpec:
    key = TemplateKey(template_id, template_version)
    if key not in _TEMPLATES:
        available = sorted([f"{k.id}@{k.version}" for k in _TEMPLATES.keys()])
        raise KeyError(f"Unknown template {template_id}@{template_version}. Available: {available}")
    return _TEMPLATES[key]


def list_templates() -> List[str]:
    return sorted([f"{k.id}@{k.version}" for k in _TEMPLATES.keys()])


# Register built-in templates
register_template(
    "groove_feedback",
    "1.0.0",
    "groove_feedback",
    "Generate constructive feedback based on groove analysis metrics.",
)

register_template(
    "practice_summary",
    "1.0.0",
    "practice_summary",
    "Generate a summary of the practice session.",
)

register_template(
    "explain_drill",
    "1.0.0",
    "explain_drill",
    "Generate coaching phrase, 2-step drill, and success cue for each teaching objective.",
)
