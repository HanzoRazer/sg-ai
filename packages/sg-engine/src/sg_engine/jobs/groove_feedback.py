# src/sg_engine/jobs/groove_feedback.py
"""
Job: groove_feedback (Wave 1)

Responsibilities:
- Analyze groove metrics from context
- Generate constructive feedback
- Cite evidence for each feedback item
- Suggest next focus area

This job returns a CoachingDraft dict.

sg-spec Integration:
    Feedback items can be converted to sg_spec.schemas.coach_schemas.CoachFinding
    using to_coach_finding(). This enables interop with the sg-spec coach
    schema layer (Mode 1 rules-based evaluation).

    Example:
        from sg_engine.coach_types import CoachFinding, Severity
        finding = to_coach_finding(feedback_item)  # -> CoachFinding
"""

from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from sg_engine.coach_types import CoachFinding

from sg_engine.templates.registry import get_template
from sg_engine.validate import validate_json_schema
from sg_engine.governance import ensure_no_pii_fields, ensure_feedback_has_evidence
from sg_engine.models.registry import get_model


SUPPORTED_TEMPLATE_ID = "groove_feedback"
SUPPORTED_TEMPLATE_VERSION = "1.0.0"


def _analyze_metrics(evidence: dict) -> List[Dict[str, Any]]:
    """
    Analyze groove metrics and generate feedback items.
    This is the core Groove Layer intelligence.
    """
    metrics = evidence.get("groove_metrics", {})
    feedback = []

    # Analyze tempo stability
    tempo = metrics.get("tempo_stability", 0)
    if tempo >= 0.8:
        feedback.append({
            "category": "strength",
            "text": "Your tempo consistency is excellent! You're maintaining a steady pulse throughout your playing.",
            "evidence_refs": [{"metric": "tempo_stability", "value": tempo}],
            "priority": 2,
        })
    elif tempo < 0.5:
        feedback.append({
            "category": "focus_area",
            "text": "Let's work on tempo consistency. Try practicing with a metronome at a slower tempo, then gradually increase speed.",
            "evidence_refs": [{"metric": "tempo_stability", "value": tempo}],
            "priority": 1,
        })

    # Analyze dynamics
    dynamics = metrics.get("dynamics_range", 0)
    if dynamics >= 0.7:
        feedback.append({
            "category": "strength",
            "text": "Great dynamic expression! Your playing has nice variation between soft and loud passages.",
            "evidence_refs": [{"metric": "dynamics_range", "value": dynamics}],
            "priority": 3,
        })
    elif dynamics < 0.5:
        feedback.append({
            "category": "focus_area",
            "text": "Try adding more dynamic contrast to your playing. Experiment with playing some phrases softer and others louder.",
            "evidence_refs": [{"metric": "dynamics_range", "value": dynamics}],
            "priority": 2,
        })

    # Analyze articulation
    articulation = metrics.get("articulation_clarity", 0)
    if articulation >= 0.75:
        feedback.append({
            "category": "strength",
            "text": "Your note articulation is clear and precise. Each note rings out distinctly.",
            "evidence_refs": [{"metric": "articulation_clarity", "value": articulation}],
            "priority": 3,
        })

    # Always add encouragement
    feedback.append({
        "category": "encouragement",
        "text": "Keep up the great work! Consistent practice is the key to improvement.",
        "evidence_refs": [{"metric": "tempo_stability", "value": tempo}],
        "priority": 5,
    })

    # Sort by priority and limit to 5
    feedback.sort(key=lambda x: x.get("priority", 5))
    return feedback[:5]


def _determine_next_focus(evidence: dict) -> Dict[str, Any]:
    """Determine the best area to focus on next."""
    metrics = evidence.get("groove_metrics", {})

    # Find weakest area
    areas = [
        ("timing", metrics.get("tempo_stability", 0.5)),
        ("dynamics", metrics.get("dynamics_range", 0.5)),
        ("articulation", metrics.get("articulation_clarity", 0.5)),
        ("phrasing", metrics.get("phrase_coherence", 0.5)),
    ]

    weakest = min(areas, key=lambda x: x[1])

    exercises = {
        "timing": "Try the 'subdivision exercise': play quarter notes, then eighths, then sixteenths, all at a steady tempo.",
        "dynamics": "Practice the same phrase at three dynamic levels: piano, mezzo-forte, and forte.",
        "articulation": "Focus on clean finger placement and even pressure across all strings.",
        "phrasing": "Listen to a recording and try to match the breathing and pauses in the melody.",
    }

    return {
        "area": weakest[0],
        "reason": f"This area shows the most room for growth based on your session.",
        "exercise_hint": exercises.get(weakest[0], ""),
    }


def _compute_groove_score(evidence: dict) -> Dict[str, Any]:
    """Compute overall groove score for UI display."""
    metrics = evidence.get("groove_metrics", {})

    values = [
        metrics.get("tempo_stability", 0.5),
        metrics.get("beat_accuracy", 0.5),
        metrics.get("dynamics_range", 0.5),
        metrics.get("articulation_clarity", 0.5),
        metrics.get("phrase_coherence", 0.5),
    ]

    overall = sum(values) / len(values) * 100

    # Determine trend (would need history in real implementation)
    trend = "stable"
    if overall >= 70:
        trend = "improving"
    elif overall < 50:
        trend = "needs_attention"

    return {
        "overall": round(overall, 1),
        "trend": trend,
    }


def run_job(context: dict) -> Dict[str, Any]:
    """
    Execute the groove_feedback job and return CoachingDraft dict.
    """
    request = context.get("request", {}) or {}
    template_id = request.get("template_id")
    template_version = request.get("template_version")
    kind = request.get("kind")

    # Hard gate
    if kind != "groove_feedback":
        raise ValueError(f"Unsupported request.kind for groove_feedback job: {kind!r}")
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
    feedback = _analyze_metrics(evidence)
    next_focus = _determine_next_focus(evidence)
    groove_score = _compute_groove_score(evidence)

    # Build draft
    draft = {
        "schema_id": "coaching_draft_v1",
        "schema_version": "v1",
        "kind": "groove_feedback",
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
        "next_focus": next_focus,
        "groove_score": groove_score,
    }

    # Generate summary
    stats = evidence.get("session_stats", {})
    duration = stats.get("duration_seconds", 0)
    notes = stats.get("notes_played", 0)
    if duration > 0:
        draft["summary"] = f"Great session! You played {notes} notes over {duration // 60} minutes."

    # Governance check on output
    ensure_no_pii_fields(draft)
    ensure_feedback_has_evidence(draft)

    return draft



# =============================================================================
# Simplified Entry Point
# =============================================================================

def run_groove_feedback(context: dict) -> Dict[str, Any]:
    """
    Simplified entry point for groove feedback generation.

    This is a convenience wrapper around run_job() that:
    - Accepts a flatter context structure (groove_metrics at top level)
    - Transforms it to the run_job format
    - Returns draft with session_id and groove_score.value for UI consumption

    Args:
        context: Dict with groove_metrics, session_stats, session_id, etc.

    Returns:
        CoachingDraft dict with feedback, groove_score, etc.
    """
    # Transform flat context to run_job format
    job_context = {
        "request": {
            "template_id": SUPPORTED_TEMPLATE_ID,
            "template_version": SUPPORTED_TEMPLATE_VERSION,
            "kind": "groove_feedback",
        },
        "evidence": {
            "groove_metrics": context.get("groove_metrics", {}),
            "session_stats": context.get("session_stats", {}),
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


# =============================================================================
# sg-spec Integration Helpers
# =============================================================================

# Mapping from groove feedback categories to sg-spec types
_CATEGORY_TO_TYPE = {
    "strength": "technique",
    "focus_area": "timing",
    "tip": "technique",
    "encouragement": "other",
}

# Mapping from groove feedback categories to sg-spec severity
_CATEGORY_TO_SEVERITY = {
    "strength": "info",
    "focus_area": "primary",
    "tip": "secondary",
    "encouragement": "info",
}


def to_coach_finding(feedback_item: Dict[str, Any]) -> "CoachFinding":
    """
    Convert a groove feedback item to a sg-spec CoachFinding.

    This enables interop with string_master's coach layer.

    Args:
        feedback_item: Dict with keys: category, text, evidence_refs, priority

    Returns:
        CoachFinding instance compatible with sg-spec
    """
    from sg_engine.coach_types import CoachFinding, FindingEvidence, Severity

    category = feedback_item.get("category", "tip")
    text = feedback_item.get("text", "")
    refs = feedback_item.get("evidence_refs", [])

    # Build evidence from first ref (if any)
    evidence_kwargs: Dict[str, Any] = {}
    if refs:
        ref = refs[0]
        if "metric" in ref:
            evidence_kwargs["metric"] = ref["metric"]
        if "value" in ref:
            evidence_kwargs["value"] = ref["value"]

    finding_type = _CATEGORY_TO_TYPE.get(category, "other")
    severity_str = _CATEGORY_TO_SEVERITY.get(category, "info")

    return CoachFinding(
        type=finding_type,  # type: ignore[arg-type]
        severity=Severity(severity_str),
        evidence=FindingEvidence(**evidence_kwargs),
        interpretation=text[:240],  # CoachFinding has max 240 chars
    )
