# src/sg_engine/jobs/practice_summary.py
"""
Job: practice_summary (Phase 1)

Responsibilities:
- Summarize practice session with stats
- Highlight achievements and progress
- Compare to previous sessions (if history available)
- Suggest goals for next practice

This job returns a CoachingDraft dict with kind="practice_summary".
"""

from __future__ import annotations

from typing import Any, Dict, List

from sg_engine.templates.registry import get_template
from sg_engine.governance import ensure_no_pii_fields, ensure_feedback_has_evidence
from sg_engine.models.registry import get_model


SUPPORTED_TEMPLATE_ID = "practice_summary"
SUPPORTED_TEMPLATE_VERSION = "1.0.0"


def _format_duration(seconds: int) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds} seconds"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{hours}h {mins}m"


def _analyze_session(evidence: dict) -> List[Dict[str, Any]]:
    """
    Analyze session data and generate summary feedback items.
    """
    stats = evidence.get("session_stats", {})
    history = evidence.get("session_history", [])
    feedback = []

    duration = stats.get("duration_seconds", 0)
    notes_played = stats.get("notes_played", 0)
    bars_completed = stats.get("bars_completed", 0)

    # Duration achievement
    if duration >= 1800:  # 30+ minutes
        feedback.append({
            "category": "strength",
            "text": f"Excellent focus! You practiced for {_format_duration(duration)} - sustained practice builds muscle memory.",
            "evidence_refs": [{"metric": "duration_seconds", "value": duration}],
            "priority": 2,
        })
    elif duration >= 900:  # 15-30 minutes
        feedback.append({
            "category": "strength",
            "text": f"Good session length at {_format_duration(duration)}. Consistent short sessions add up!",
            "evidence_refs": [{"metric": "duration_seconds", "value": duration}],
            "priority": 3,
        })
    elif duration > 0:
        feedback.append({
            "category": "tip",
            "text": f"You practiced for {_format_duration(duration)}. Even short sessions count - try to build up to 15 minutes.",
            "evidence_refs": [{"metric": "duration_seconds", "value": duration}],
            "priority": 4,
        })

    # Note count achievement
    if notes_played >= 500:
        feedback.append({
            "category": "strength",
            "text": f"High activity session with {notes_played} notes played! Your fingers are getting a workout.",
            "evidence_refs": [{"metric": "notes_played", "value": notes_played}],
            "priority": 3,
        })
    elif notes_played >= 100:
        feedback.append({
            "category": "encouragement",
            "text": f"You played {notes_played} notes this session. Every note is progress!",
            "evidence_refs": [{"metric": "notes_played", "value": notes_played}],
            "priority": 4,
        })

    # Progress comparison (if history available)
    if history and len(history) >= 2:
        prev_duration = history[-2].get("duration_seconds", 0) if len(history) >= 2 else 0
        if duration > prev_duration * 1.2:  # 20% improvement
            feedback.append({
                "category": "strength",
                "text": "You practiced longer than your previous session - great commitment!",
                "evidence_refs": [
                    {"metric": "duration_seconds", "value": duration},
                    {"metric": "previous_duration", "value": prev_duration},
                ],
                "priority": 2,
            })

        # Streak detection
        streak = 0
        for session in reversed(history):
            if session.get("completed", False):
                streak += 1
            else:
                break
        if streak >= 3:
            feedback.append({
                "category": "strength",
                "text": f"You're on a {streak}-session streak! Consistency is the key to mastery.",
                "evidence_refs": [{"metric": "session_streak", "value": streak}],
                "priority": 1,
            })

    # Always add encouragement
    feedback.append({
        "category": "encouragement",
        "text": "Great work showing up to practice! The best players are the ones who keep coming back.",
        "evidence_refs": [{"metric": "session_completed", "value": 1}],
        "priority": 5,
    })

    # Sort by priority and limit to 5
    feedback.sort(key=lambda x: x.get("priority", 5))
    return feedback[:5]


def _compute_session_score(evidence: dict) -> Dict[str, Any]:
    """Compute session engagement score."""
    stats = evidence.get("session_stats", {})
    history = evidence.get("session_history", [])

    duration = stats.get("duration_seconds", 0)
    notes_played = stats.get("notes_played", 0)

    # Normalize metrics to 0-100 scale
    duration_score = min(100, (duration / 1800) * 100)  # 30 min = 100
    activity_score = min(100, (notes_played / 500) * 100)  # 500 notes = 100

    overall = (duration_score * 0.4 + activity_score * 0.6)

    # Determine trend from history
    trend = "stable"
    if len(history) >= 2:
        prev_duration = history[-2].get("duration_seconds", 0)
        if duration > prev_duration * 1.1:
            trend = "improving"
        elif duration < prev_duration * 0.9:
            trend = "needs_attention"

    return {
        "overall": round(overall, 1),
        "trend": trend,
    }


def _determine_next_goal(evidence: dict) -> Dict[str, Any]:
    """Suggest next practice goal based on session data."""
    stats = evidence.get("session_stats", {})
    groove_metrics = evidence.get("groove_metrics", {})

    duration = stats.get("duration_seconds", 0)
    tempo_stability = groove_metrics.get("tempo_stability", 0.5)

    # Goal suggestions based on current state
    if duration < 600:  # Less than 10 minutes
        return {
            "area": "consistency",
            "reason": "Building a regular practice habit is foundational.",
            "exercise_hint": "Try to practice for at least 15 minutes tomorrow.",
        }
    elif tempo_stability < 0.6:
        return {
            "area": "timing",
            "reason": "Tempo consistency will make everything else easier.",
            "exercise_hint": "Start your next session with 5 minutes of metronome work.",
        }
    else:
        return {
            "area": "repertoire",
            "reason": "Your fundamentals are solid - time to expand!",
            "exercise_hint": "Try learning a new chord or short phrase next session.",
        }


def _generate_summary(evidence: dict) -> str:
    """Generate a brief session summary."""
    stats = evidence.get("session_stats", {})
    duration = stats.get("duration_seconds", 0)
    notes_played = stats.get("notes_played", 0)
    program_name = stats.get("program_name", "your practice")

    parts = []
    if duration > 0:
        parts.append(f"{_format_duration(duration)} of practice")
    if notes_played > 0:
        parts.append(f"{notes_played} notes played")

    if parts:
        return f"Session complete: {', '.join(parts)}. Well done!"
    return "Session complete. Every practice session counts!"


def run_job(context: dict) -> Dict[str, Any]:
    """
    Execute the practice_summary job and return CoachingDraft dict.
    """
    request = context.get("request", {}) or {}
    template_id = request.get("template_id")
    template_version = request.get("template_version")
    kind = request.get("kind")

    # Hard gate
    if kind != "practice_summary":
        raise ValueError(f"Unsupported request.kind for practice_summary job: {kind!r}")
    if template_id != SUPPORTED_TEMPLATE_ID or template_version != SUPPORTED_TEMPLATE_VERSION:
        raise ValueError(
            f"Unsupported template {template_id}@{template_version}. "
            f"Supported: {SUPPORTED_TEMPLATE_ID}@{SUPPORTED_TEMPLATE_VERSION}"
        )

    # Get evidence
    evidence = context.get("evidence", {})

    # Governance check on input
    ensure_no_pii_fields(context)

    # Get model (for provenance)
    model = get_model()

    # Analyze and generate feedback
    feedback = _analyze_session(evidence)
    session_score = _compute_session_score(evidence)
    next_goal = _determine_next_goal(evidence)
    summary = _generate_summary(evidence)

    # Build draft
    draft = {
        "schema_id": "coaching_draft_v1",
        "schema_version": "v1",
        "kind": "practice_summary",
        "model": {
            "id": model.model_id(),
            "version": model.model_version(),
            "runtime": "local",
        },
        "template": {
            "id": SUPPORTED_TEMPLATE_ID,
            "version": SUPPORTED_TEMPLATE_VERSION,
        },
        "feedback": feedback,
        "summary": summary,
        "next_focus": next_goal,
        "groove_score": session_score,  # Reuse groove_score structure for UI
    }

    # Governance check on output
    ensure_no_pii_fields(draft)
    ensure_feedback_has_evidence(draft)

    return draft


# =============================================================================
# Simplified Entry Point
# =============================================================================

def run_practice_summary(context: dict) -> Dict[str, Any]:
    """
    Simplified entry point for practice summary generation.

    Args:
        context: Dict with session_stats, session_history, session_id, etc.

    Returns:
        CoachingDraft dict with feedback, summary, etc.
    """
    # Transform flat context to run_job format
    job_context = {
        "request": {
            "template_id": SUPPORTED_TEMPLATE_ID,
            "template_version": SUPPORTED_TEMPLATE_VERSION,
            "kind": "practice_summary",
        },
        "evidence": {
            "session_stats": context.get("session_stats", {}),
            "session_history": context.get("session_history", []),
            "groove_metrics": context.get("groove_metrics", {}),
        },
    }

    # Run the job
    draft = run_job(job_context)

    # Add session_id to output for API compatibility
    draft["session_id"] = context.get("session_id", "unknown")

    # Transform groove_score to have 'value' key for UI
    if "groove_score" in draft:
        score = draft["groove_score"]
        draft["groove_score"] = {
            "value": score.get("overall", 0),
            "trend": score.get("trend", "stable"),
        }

    return draft
