# src/sg_engine/coach_types.py
"""
sg_engine coach types — re-exported from sg_spec.schemas.coach_schemas.

This module provides access to the canonical coach types from sg-spec.

Groove Layer (sg-ai) produces:
- FeedbackItem (local) that maps to CoachFinding (sg-spec)
- FocusArea (local) that maps to FocusRecommendation (sg-spec)

For deep integration, use sg_spec.schemas.coach_schemas directly.
"""
from sg_spec.schemas.coach_schemas import (
    # Type aliases
    Sha256,
    # Enums
    Severity,
    CoachMode,
    # Evidence types
    FindingEvidence,
    CoachFinding,
    FocusRecommendation,
    # Full evaluation
    CoachEvaluation,
    # Session types (for context)
    SessionRecord,
    PerformanceSummary,
)

__all__ = [
    # Type aliases
    "Sha256",
    # Enums
    "Severity",
    "CoachMode",
    # Evidence types
    "FindingEvidence",
    "CoachFinding",
    "FocusRecommendation",
    # Full evaluation
    "CoachEvaluation",
    # Session types
    "SessionRecord",
    "PerformanceSummary",
]
