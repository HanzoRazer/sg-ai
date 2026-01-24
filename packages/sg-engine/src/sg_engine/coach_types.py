# src/sg_engine/coach_types.py
"""
sg_engine coach types — re-exported from sg_spec.ai.coach.

This module provides access to the canonical coach types from sg-spec.
Use these types for consistent data exchange with string_master.

Groove Layer (sg-ai) produces:
- FeedbackItem (local) that maps to CoachFinding (sg-spec)
- FocusArea (local) that maps to FocusRecommendation (sg-spec)

For deep integration, use sg_spec.ai.coach.schemas directly.
"""
from sg_spec.ai.coach.schemas import (
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
