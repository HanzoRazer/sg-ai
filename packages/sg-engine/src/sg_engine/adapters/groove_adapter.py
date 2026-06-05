# sg_engine/adapters/groove_adapter.py
"""
Adapters for transforming sg-spec models to sg-ai job contexts.

These adapters bridge the gap between:
- sg-spec: Data shapes (Pydantic models, JSON Schema)
- sg-ai: Job context dictionaries for coaching jobs

Design Principle:
- Adapters are pure functions (no side effects)
- Input: sg-spec Pydantic model
- Output: dict suitable for sg-ai job context
- All transformations are explicit and auditable
"""

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    # Import types for static analysis only
    from sg_spec.schemas.groove_layer import GrooveProfileV1
    from sg_spec.schemas.coach_schemas import CoachEvaluation, SessionRecord


def groove_profile_to_metrics(profile: "GrooveProfileV1") -> Dict[str, Any]:
    """
    Transform a GrooveProfileV1 into groove_metrics for job context.

    The GrooveProfileV1 contains persistent player characteristics.
    This adapter extracts the metrics relevant for coaching feedback.

    Args:
        profile: GrooveProfileV1 from sg-spec

    Returns:
        Dict suitable for context["evidence"]["groove_metrics"]

    Example:
        >>> from sg_spec.schemas.groove_layer import GrooveProfileV1
        >>> profile = load_profile(...)
        >>> metrics = groove_profile_to_metrics(profile)
        >>> draft = run_groove_feedback({"groove_metrics": metrics})
    """
    # Extract timing metrics
    timing = profile.timing_bias
    tempo = profile.tempo_stability
    subdivision = profile.subdivision_fidelity
    elasticity = profile.groove_elasticity
    recovery = profile.error_recovery

    # Map to sg-ai groove_metrics format
    # Normalize confidence values to 0-1 scale
    return {
        # Core timing metrics
        "tempo_stability": tempo.confidence,  # How stable is the tempo
        "beat_accuracy": 1.0 - min(1.0, abs(timing.mean_offset_ms) / 50.0),  # Invert offset to accuracy

        # Dynamics (derived from elasticity)
        "dynamics_range": elasticity.lock_threshold,  # How dynamic the playing is

        # Articulation (derived from subdivision fidelity)
        "articulation_clarity": subdivision.confidence,

        # Phrasing (derived from elasticity)
        "phrase_coherence": subdivision.swing_tolerance,

        # Additional context for advanced analysis
        "_profile_context": {
            "timing_direction": timing.direction,
            "tempo_range": list(tempo.supported_bpm_range),
            "subdivisions_supported": subdivision.supported,
            "subdivisions_unstable": subdivision.unstable,
            "push_pull_balance": elasticity.push_pull_balance,
            "recovery_rate": recovery.self_correction_rate,
            "panic_probability": recovery.panic_probability,
        },

        # Confidence band for uncertainty quantification
        "_confidence": {
            "lower": profile.confidence_band.lower,
            "upper": profile.confidence_band.upper,
        },

        # Evidence window
        "_evidence": {
            "sessions": profile.evidence_window.sessions,
            "events": profile.evidence_window.events,
        },
    }


def coach_evaluation_to_context(evaluation: "CoachEvaluation") -> Dict[str, Any]:
    """
    Transform a CoachEvaluation into context for practice_summary job.

    The CoachEvaluation contains the coaching layer's interpretation
    of a session. This adapter extracts fields for summary generation.

    Args:
        evaluation: CoachEvaluation from sg-spec

    Returns:
        Dict suitable for extending job context
    """
    return {
        "coach_findings": [
            {
                "type": f.type,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "interpretation": f.interpretation,
                "step": f.evidence.step if f.evidence else None,
                "error_ms": f.evidence.mean_error_ms if f.evidence else None,
            }
            for f in evaluation.findings
        ],
        "strengths": list(evaluation.strengths) if evaluation.strengths else [],
        "weaknesses": list(evaluation.weaknesses) if evaluation.weaknesses else [],
        "focus_recommendation": {
            "concept": evaluation.focus_recommendation.concept,
            "reason": evaluation.focus_recommendation.reason,
        },
        "confidence": evaluation.confidence,
    }


def session_record_to_stats(session: "SessionRecord") -> Dict[str, Any]:
    """
    Transform a SessionRecord into session_stats for job context.

    The SessionRecord contains immutable facts about a practice session.
    This adapter extracts the statistical summary for coaching jobs.

    Args:
        session: SessionRecord from sg-spec

    Returns:
        Dict suitable for context["evidence"]["session_stats"]
    """
    perf = session.performance
    events = session.events

    return {
        "duration_seconds": session.duration_s,
        "notes_played": perf.notes_played,
        "notes_expected": perf.notes_expected,
        "notes_dropped": perf.notes_dropped,
        "bars_completed": perf.bars_played,

        # Timing stats
        "timing_error_mean_ms": perf.timing_error_ms.mean if perf.timing_error_ms else None,
        "timing_error_std_ms": perf.timing_error_ms.std if perf.timing_error_ms else None,
        "timing_error_max_ms": perf.timing_error_ms.max if perf.timing_error_ms else None,

        # Events
        "late_drops": events.late_drops if events else 0,
        "panic_triggered": events.panic_triggered if events else False,

        # Program info
        "program_name": session.program_ref.name if session.program_ref else None,
        "program_type": session.program_ref.type.value if session.program_ref else None,

        # Timing config
        "bpm": session.timing.bpm if session.timing else None,
        "grid": session.timing.grid if session.timing else None,
    }


def build_groove_feedback_context(
    profile: "GrooveProfileV1",
    session: "SessionRecord",
    session_id: str | None = None,
) -> Dict[str, Any]:
    """
    Build complete context for groove_feedback job from sg-spec models.

    This is the main entry point for integrating sg-spec with sg-ai.

    Args:
        profile: GrooveProfileV1 with player characteristics
        session: SessionRecord with session facts
        session_id: Optional session ID override

    Returns:
        Complete context dict ready for run_groove_feedback()

    Example:
        >>> from sg_spec.schemas.groove_layer import GrooveProfileV1
        >>> from sg_spec.schemas.coach_schemas import SessionRecord
        >>> from sg_engine.adapters import build_groove_feedback_context
        >>> from sg_engine.jobs.groove_feedback import run_groove_feedback
        >>>
        >>> profile = load_profile(...)
        >>> session = get_session_record(...)
        >>> context = build_groove_feedback_context(profile, session)
        >>> draft = run_groove_feedback(context)
    """
    return {
        "session_id": session_id or str(session.session_id),
        "groove_metrics": groove_profile_to_metrics(profile),
        "session_stats": session_record_to_stats(session),
    }


def build_practice_summary_context(
    session: "SessionRecord",
    evaluation: "CoachEvaluation | None" = None,
    session_history: list[Dict[str, Any]] | None = None,
    session_id: str | None = None,
) -> Dict[str, Any]:
    """
    Build complete context for practice_summary job from sg-spec models.

    Args:
        session: SessionRecord with session facts
        evaluation: Optional CoachEvaluation for richer context
        session_history: Optional list of previous session summaries
        session_id: Optional session ID override

    Returns:
        Complete context dict ready for run_practice_summary()
    """
    context = {
        "session_id": session_id or str(session.session_id),
        "session_stats": session_record_to_stats(session),
        "session_history": session_history or [],
    }

    if evaluation:
        context["coach_context"] = coach_evaluation_to_context(evaluation)

    return context
