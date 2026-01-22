# src/sg_engine/models/registry.py
"""
Local model registry for sg-ai.

v1 goal:
- Provide a stable interface for on-device model invocation.
- Keep dependencies minimal.
- Support a rule-based "model" for deterministic coaching.

The Groove Layer is primarily rule-based in v1, with optional
LLM enhancement in future versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional


class LocalModel(Protocol):
    def model_id(self) -> str: ...
    def model_version(self) -> str: ...


@dataclass
class GrooveLayerModel:
    """
    Groove Layer rule-based model.

    v1 is deterministic rule-based coaching.
    Future versions may integrate small LLMs for natural language generation.
    """
    _id: str = "groove-layer-rules"
    _version: str = "1.0.0"

    def model_id(self) -> str:
        return self._id

    def model_version(self) -> str:
        return self._version


# Singleton
_MODEL_SINGLETON: Optional[LocalModel] = None


def get_model() -> LocalModel:
    """
    Return the configured local model adapter.

    v1 default is GrooveLayerModel (rule-based).
    """
    global _MODEL_SINGLETON
    if _MODEL_SINGLETON is None:
        _MODEL_SINGLETON = GrooveLayerModel()
    return _MODEL_SINGLETON


def set_model_for_tests(model: LocalModel) -> None:
    """Test hook to swap model adapter."""
    global _MODEL_SINGLETON
    _MODEL_SINGLETON = model
