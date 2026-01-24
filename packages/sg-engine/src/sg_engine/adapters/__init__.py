# sg_engine/adapters — data format adapters
"""
Adapters for transforming between sg-spec data models and sg-ai job contexts.

The sg-spec repository owns the canonical data shapes (Pydantic models).
The sg-ai repository consumes these shapes and transforms them into
job-specific context formats.

This module provides the bridge between:
- GrooveProfileV1 (sg-spec) → groove_metrics (sg-ai job context)
- CoachEvaluation (sg-spec) → feedback context (sg-ai job context)
"""

from sg_engine.adapters.groove_adapter import (
    groove_profile_to_metrics,
    coach_evaluation_to_context,
    session_record_to_stats,
)

__all__ = [
    "groove_profile_to_metrics",
    "coach_evaluation_to_context",
    "session_record_to_stats",
]
