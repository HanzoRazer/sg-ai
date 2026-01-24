# src/sg_engine/jobs/timing_feedback.py
"""
Job: timing_feedback — "Why Am I Off?"

Responsibilities:
- Analyze timing errors from session data (error_by_step)
- Map step numbers to human-readable musical positions
- Generate clear explanation of timing issues
- Suggest targeted exercises to fix specific problems

This job is designed for beginners who struggle with timing
and need concrete, actionable feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from sg_engine.governance import ensure_no_pii_fields


# =============================================================================
# Musical Position Mapping
# =============================================================================

# Step names for 16th-note grid (grid=16)
# Steps 0-15 map to subdivisions of a 4/4 bar
_STEP_NAMES_16 = {
    0: ("1", "beat 1", "downbeat"),
    1: ("1e", "the 'e' of 1", "first sixteenth after beat 1"),
    2: ("1&", "the 'and' of 1", "eighth note after beat 1"),
    3: ("1a", "the 'a' of 1", "last sixteenth before beat 2"),
    4: ("2", "beat 2", "backbeat"),
    5: ("2e", "the 'e' of 2", "first sixteenth after beat 2"),
    6: ("2&", "the 'and' of 2", "eighth note after beat 2"),
    7: ("2a", "the 'a' of 2", "last sixteenth before beat 3"),
    8: ("3", "beat 3", "third beat"),
    9: ("3e", "the 'e' of 3", "first sixteenth after beat 3"),
    10: ("3&", "the 'and' of 3", "eighth note after beat 3"),
    11: ("3a", "the 'a' of 3", "last sixteenth before beat 4"),
    12: ("4", "beat 4", "fourth beat"),
    13: ("4e", "the 'e' of 4", "first sixteenth after beat 4"),
    14: ("4&", "the 'and' of 4", "eighth note after beat 4"),
    15: ("4a", "the 'a' of 4", "pickup into next bar"),
}

# Clave hit steps for common patterns (grid=16)
_CLAVE_HITS = {
    "son_2_3": {0, 3, 6, 10, 12},  # 2-3 son clave
    "son_3_2": {0, 4, 6, 10, 12},  # 3-2 son clave
    "rumba_2_3": {0, 3, 7, 10, 12},  # 2-3 rumba clave
}


def step_to_position(step: int, grid: int = 16) -> Dict[str, str]:
    """
    Convert a step number to human-readable musical position.

    Args:
        step: Step number (0-based, wraps at grid)
        grid: Grid subdivision (8 or 16)

    Returns:
        Dict with 'short', 'medium', 'long' descriptions
    """
    step = step % grid

    if grid == 16:
        if step in _STEP_NAMES_16:
            short, medium, long = _STEP_NAMES_16[step]
            return {"short": short, "medium": medium, "long": long}

    # Fallback for other grids
    beat = (step // (grid // 4)) + 1
    subdivision = step % (grid // 4)

    if subdivision == 0:
        return {
            "short": str(beat),
            "medium": f"beat {beat}",
            "long": f"beat {beat} (downbeat)" if beat == 1 else f"beat {beat}",
        }
    else:
        return {
            "short": f"{beat}+{subdivision}",
            "medium": f"subdivision {subdivision} of beat {beat}",
            "long": f"the {subdivision}th subdivision after beat {beat}",
        }


def is_clave_hit(step: int, clave: str = "son_2_3", grid: int = 16) -> bool:
    """Check if a step is a clave accent."""
    step = step % grid
    hits = _CLAVE_HITS.get(clave, set())
    return step in hits


# =============================================================================
# Timing Issue Analysis
# =============================================================================

TimingDirection = Literal["early", "late", "on_time"]


def classify_error(error_ms: float, threshold_ms: float = 15.0) -> TimingDirection:
    """Classify timing error as early, late, or on_time."""
    if error_ms > threshold_ms:
        return "late"
    elif error_ms < -threshold_ms:
        return "early"
    return "on_time"


def analyze_timing_issues(
    error_by_step: Dict[str, float],
    grid: int = 16,
    clave: str = "son_2_3",
    threshold_ms: float = 20.0,
) -> List[Dict[str, Any]]:
    """
    Analyze timing errors and identify problematic steps.

    Args:
        error_by_step: Dict mapping step (as string) to error in ms
                       Positive = late, negative = early
        grid: Grid subdivision
        clave: Clave pattern name
        threshold_ms: Minimum error to flag as issue

    Returns:
        List of issue dicts, sorted by severity (worst first)
    """
    issues = []

    for step_str, error_ms in error_by_step.items():
        try:
            step = int(step_str)
        except ValueError:
            continue

        abs_error = abs(error_ms)
        if abs_error < threshold_ms:
            continue

        direction = classify_error(error_ms, threshold_ms=0)
        position = step_to_position(step, grid)
        on_clave = is_clave_hit(step, clave, grid)

        # Severity: clave hits matter more, larger errors matter more
        severity = abs_error
        if on_clave:
            severity *= 1.5  # Clave timing errors are more noticeable

        issues.append({
            "step": step,
            "error_ms": round(error_ms, 1),
            "abs_error_ms": round(abs_error, 1),
            "direction": direction,
            "position": position,
            "on_clave": on_clave,
            "severity": severity,
        })

    # Sort by severity (worst first)
    issues.sort(key=lambda x: x["severity"], reverse=True)
    return issues


# =============================================================================
# Explanation Generation
# =============================================================================

_DIRECTION_VERBS = {
    "early": ("rushing", "pushing", "anticipating"),
    "late": ("dragging", "lagging", "falling behind on"),
}

_CLAVE_CONTEXT = {
    0: "the foundation of the groove",
    3: "the clave push — it should pull you forward",
    6: "the syncopated accent",
    10: "the anticipation into beat 4",
    12: "the resolution point",
}


def generate_explanation(
    issues: List[Dict[str, Any]],
    max_issues: int = 3,
) -> str:
    """
    Generate human-readable explanation of timing issues.

    Args:
        issues: List of issue dicts from analyze_timing_issues()
        max_issues: Maximum number of issues to explain

    Returns:
        Human-friendly explanation string
    """
    if not issues:
        return "Your timing looks solid! No significant issues detected."

    top_issues = issues[:max_issues]

    if len(top_issues) == 1:
        issue = top_issues[0]
        return _explain_single_issue(issue)

    # Multiple issues
    lines = ["Here's what I'm hearing:"]
    for i, issue in enumerate(top_issues, 1):
        lines.append(f"{i}. {_explain_single_issue(issue, brief=True)}")

    # Add pattern observation if issues share a characteristic
    directions = [i["direction"] for i in top_issues]
    if all(d == "late" for d in directions):
        lines.append("\nOverall pattern: You're consistently behind the beat. Try thinking slightly ahead.")
    elif all(d == "early" for d in directions):
        lines.append("\nOverall pattern: You're rushing. Take a breath and let the beat come to you.")

    return "\n".join(lines)


def _explain_single_issue(issue: Dict[str, Any], brief: bool = False) -> str:
    """Generate explanation for a single timing issue."""
    direction = issue["direction"]
    position = issue["position"]
    error_ms = issue["error_ms"]
    step = issue["step"]
    on_clave = issue["on_clave"]

    verbs = _DIRECTION_VERBS.get(direction, ("off on",))
    verb = verbs[0]

    if brief:
        return f"You're {verb} {position['medium']} by {abs(error_ms):.0f}ms"

    # Full explanation
    explanation = f"You're {verb} {position['medium']} by about {abs(error_ms):.0f} milliseconds."

    # Add clave context if relevant
    if on_clave and step in _CLAVE_CONTEXT:
        explanation += f" This is {_CLAVE_CONTEXT[step]}."

    # Add feel description
    if direction == "late":
        if abs(error_ms) > 35:
            explanation += " It's noticeably dragging — the groove feels heavy."
        else:
            explanation += " It's making the groove feel laid back, maybe too relaxed."
    else:  # early
        if abs(error_ms) > 35:
            explanation += " It's rushing ahead — the groove feels anxious."
        else:
            explanation += " It's pushing the beat, creating tension."

    return explanation


# =============================================================================
# Exercise Generation
# =============================================================================

_STEP_EXERCISES = {
    # Beat 1 issues
    0: {
        "title": "Downbeat Lock",
        "description": "Count '1-2-3-4' out loud. Play ONLY on '1' for 8 bars. Feel the weight of the downbeat.",
        "focus": "Feel beat 1 as the anchor. Everything flows from here.",
    },
    # And-of-2 issues (common problem spot)
    6: {
        "title": "Backbeat Push",
        "description": "Count '1-and-2-AND-3-and-4-and'. Clap only on the capitalized AND (the 'and' of 2). Do this for 16 bars before playing.",
        "focus": "The 'and' of 2 should feel like it's pulling you into beat 3.",
    },
    # And-of-4 / pickup issues
    14: {
        "title": "Pickup Practice",
        "description": "Count a full bar, then play ONE note on the 'and' of 4. Let it lead into the next bar's beat 1. Repeat 8 times.",
        "focus": "The pickup anticipates the next bar — it should feel like a breath before speaking.",
    },
}

_DIRECTION_EXERCISES = {
    "late": {
        "title": "Think Ahead",
        "description": "Imagine the beat happening slightly BEFORE you hear it. Play to where the beat WILL be, not where it was.",
        "focus": "Mental anticipation. Hear it in your head before your hands move.",
    },
    "early": {
        "title": "Wait For It",
        "description": "Take a breath on beat 4. Let beat 1 come to you. Don't chase it.",
        "focus": "Patience. The groove has space — use it.",
    },
}

_CLAVE_EXERCISE = {
    "title": "Clave Lock",
    "description": "Listen to just the clave pattern. Tap along until you can feel where each hit lands. Then play your part while keeping the clave in your mind.",
    "focus": "The clave is the skeleton. Everything hangs on it.",
}


def suggest_exercises(
    issues: List[Dict[str, Any]],
    max_exercises: int = 2,
) -> List[Dict[str, Any]]:
    """
    Suggest targeted exercises based on timing issues.

    Args:
        issues: List of issue dicts from analyze_timing_issues()
        max_exercises: Maximum number of exercises to suggest

    Returns:
        List of exercise dicts with title, description, focus
    """
    if not issues:
        return [{
            "title": "Maintenance Mode",
            "description": "Your timing is good! Keep practicing with the click track to maintain your accuracy.",
            "focus": "Consistency through repetition.",
        }]

    exercises = []
    seen_types = set()

    for issue in issues:
        if len(exercises) >= max_exercises:
            break

        step = issue["step"]
        direction = issue["direction"]
        on_clave = issue["on_clave"]

        # Step-specific exercise
        if step in _STEP_EXERCISES and f"step_{step}" not in seen_types:
            exercises.append(_STEP_EXERCISES[step])
            seen_types.add(f"step_{step}")
            continue

        # Direction-based exercise
        if direction in _DIRECTION_EXERCISES and f"dir_{direction}" not in seen_types:
            exercises.append(_DIRECTION_EXERCISES[direction])
            seen_types.add(f"dir_{direction}")
            continue

        # Clave exercise for clave-hit issues
        if on_clave and "clave" not in seen_types:
            exercises.append(_CLAVE_EXERCISE)
            seen_types.add("clave")
            continue

    # Fallback if we couldn't find specific exercises
    if not exercises:
        exercises.append(_DIRECTION_EXERCISES.get(
            issues[0]["direction"],
            _DIRECTION_EXERCISES["late"]
        ))

    return exercises


# =============================================================================
# Main Job Entry Points
# =============================================================================

def run_timing_feedback(context: dict) -> Dict[str, Any]:
    """
    Main entry point: "Why Am I Off?"

    Args:
        context: Dict with:
            - error_by_step: Dict[str, float] — step -> error_ms (positive=late)
            - grid: int — 8 or 16 (default 16)
            - clave: str — clave pattern name (default "son_2_3")
            - session_id: str — optional session identifier
            - timing_error_ms: Dict with mean/std/max — optional aggregate stats

    Returns:
        Dict with:
            - kind: "timing_feedback"
            - explanation: str — human-readable explanation
            - issues: List[Dict] — detailed issue breakdown
            - exercises: List[Dict] — suggested exercises
            - summary: str — one-line summary for UI
    """
    # Extract inputs
    error_by_step = context.get("error_by_step", {})
    grid = context.get("grid", 16)
    clave = context.get("clave", "son_2_3")
    session_id = context.get("session_id", "unknown")
    timing_stats = context.get("timing_error_ms", {})

    # Governance check
    ensure_no_pii_fields(context)

    # Analyze
    issues = analyze_timing_issues(error_by_step, grid=grid, clave=clave)

    # Generate outputs
    explanation = generate_explanation(issues)
    exercises = suggest_exercises(issues)

    # Build summary
    if not issues:
        summary = "Your timing is on point!"
    elif len(issues) == 1:
        summary = f"Main issue: {issues[0]['direction']} on {issues[0]['position']['medium']}"
    else:
        summary = f"Found {len(issues)} timing issues. Focus on {issues[0]['position']['medium']} first."

    # Build draft
    draft = {
        "kind": "timing_feedback",
        "session_id": session_id,
        "explanation": explanation,
        "issues": issues,
        "exercises": exercises,
        "summary": summary,
    }

    # Add aggregate stats if available
    if timing_stats:
        draft["timing_stats"] = {
            "mean_ms": timing_stats.get("mean", 0),
            "std_ms": timing_stats.get("std", 0),
            "max_ms": timing_stats.get("max", 0),
        }

    # Governance check on output
    ensure_no_pii_fields(draft)

    return draft


def why_am_i_off(
    error_by_step: Dict[str, float],
    grid: int = 16,
    clave: str = "son_2_3",
) -> str:
    """
    Convenience function: Get just the explanation string.

    This is the "one button, one answer" interface.

    Args:
        error_by_step: Dict mapping step (as string) to error in ms
        grid: Grid subdivision (8 or 16)
        clave: Clave pattern name

    Returns:
        Human-readable explanation string
    """
    context = {
        "error_by_step": error_by_step,
        "grid": grid,
        "clave": clave,
    }
    result = run_timing_feedback(context)

    # Combine explanation and first exercise
    explanation = result["explanation"]
    exercises = result.get("exercises", [])

    if exercises:
        ex = exercises[0]
        explanation += f"\n\nTry this — {ex['title']}:\n{ex['description']}"

    return explanation
