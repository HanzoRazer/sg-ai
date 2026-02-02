# src/sg_engine/jobs/explain_drill.py
"""
Job: explain_drill (Explain + Drill Pack v1)

Responsibilities:
- Take teaching_objectives[] from sg-coach
- Generate drill_packs[] with coaching phrase, 2 drill steps, success cue
- No timing, modality, or gating decisions (sg-coach owns those)

This job returns a CoachingDraft dict with drill_packs[].
"""

from __future__ import annotations

from typing import Any

from sg_engine.governance import ensure_feedback_has_evidence, ensure_no_pii_fields

SUPPORTED_TEMPLATE_ID = "explain_drill"
SUPPORTED_TEMPLATE_VERSION = "1.0.0"


# -----------------------------------------------------------------------------
# Drill Content Library (rules-based, no LLM)
# -----------------------------------------------------------------------------

# Skill-specific coaching content keyed by skill_area
SKILL_LIBRARY: dict[str, dict[str, Any]] = {
    "tempo": {
        "coaching_phrases": [
            "Lock into the pulse like a heartbeat—steady and unwavering.",
            "The groove lives in consistency. Own the tempo, don't chase it.",
            "Think of tempo as your anchor. Everything else flows from it.",
        ],
        "drill_templates": [
            (
                "Set metronome to {bpm} BPM. Tap your foot on each click for 30s before playing.",
                "Play only beat 1 for 8 bars, letting the metronome fill beats 2-4.",
            ),
            (
                "Practice at half tempo ({half_bpm} BPM) until each note lands on the click.",
                "Increase by 5 BPM only when you nail 4 bars perfectly.",
            ),
            (
                "Record 8 bars, then listen back while watching the metronome.",
                "Find the exact beat where you rush or drag, then loop that section.",
            ),
        ],
        "success_cues": [
            "You feel the click as part of your body, not something external to chase.",
            "The metronome disappears because you and it are perfectly aligned.",
            "You could remove the click and still land every beat in the same spot.",
        ],
    },
    "dynamics": {
        "coaching_phrases": [
            "Dynamics are the emotional arc of your playing—let the music breathe.",
            "Soft isn't weak, loud isn't strong. Both are intentional choices.",
            "Control your touch like a volume knob you can turn with precision.",
        ],
        "drill_templates": [
            (
                "Play a scale from pianissimo to fortissimo over 8 notes.",
                "Reverse it: start loud, end soft. Each note is a distinct volume step.",
            ),
            (
                "Play one phrase three ways: whisper, conversational, commanding.",
                "Record all three. Listen for whether each version sounds different.",
            ),
            (
                "Accent only beat 1 of each bar while keeping other notes soft.",
                "Shift the accent to beat 2, then 3, then 4. Feel the groove change.",
            ),
        ],
        "success_cues": [
            "Someone across the room could tell which notes you meant to emphasize.",
            "Soft notes have presence; loud notes have power without strain.",
            "You can hear the 'shape' of each phrase—beginning, peak, resolution.",
        ],
    },
    "articulation": {
        "coaching_phrases": [
            "Clean articulation: every note has its own identity—clear start and end.",
            "Think of each note as a word. Mumbling loses meaning; clarity wins.",
            "Precision isn't stiffness. Know exactly where each note begins and ends.",
        ],
        "drill_templates": [
            (
                "Play a 4-note pattern staccato (short, detached). Leave silence between.",
                "Now play legato (smooth, connected). Notice the difference in sustain.",
            ),
            (
                "Play the same note 10 times, making each attack identical.",
                "Then vary: some soft-picked, some snappy. Control the contrast.",
            ),
            (
                "Record a phrase. Count how many notes blur versus ring clearly.",
                "Re-record aiming for zero blurred notes, even if you slow down.",
            ),
        ],
        "success_cues": [
            "Each note rings clearly with no fret buzz or muted strings.",
            "You hear daylight between staccato notes; smooth connection in legato.",
            "A listener could transcribe your notes because none blur together.",
        ],
    },
    "phrasing": {
        "coaching_phrases": [
            "Phrasing tells a story. Every phrase has beginning, middle, and end.",
            "Think in sentences, not words. Let your phrases breathe and resolve.",
            "The space between phrases matters as much as the notes themselves.",
        ],
        "drill_templates": [
            (
                "Sing the melody first (even badly). Notice where you naturally breathe.",
                "Play on guitar, breathing at the same spots. Pauses define phrases.",
            ),
            (
                "Mark phrase boundaries in your music. Play each as a complete thought.",
                "Experiment with extending or shortening the pause between phrases.",
            ),
            (
                "Record yourself and mark where phrases feel rushed or incomplete.",
                "Re-record, giving each phrase its full arc before the next.",
            ),
        ],
        "success_cues": [
            "A listener knows where one musical thought ends and the next begins.",
            "Pauses feel intentional, not accidental. Silence is part of the music.",
            "Each phrase feels like a complete sentence, not a fragment.",
        ],
    },
    "rhythm": {
        "coaching_phrases": [
            "Rhythm is the skeleton of music. Get it right; everything else follows.",
            "Feel the subdivisions. Every beat has a micro-grid you can lock into.",
            "Syncopation isn't chaos—it's notes placed exactly where expected.",
        ],
        "drill_templates": [
            (
                "Clap the rhythm without playing notes. Just the timing pattern.",
                "Once you clap it perfectly, add notes while keeping the same feel.",
            ),
            (
                "Practice with a drum loop instead of a metronome. Lock to kick/snare.",
                "If you drift, stop and re-sync. The drums don't lie.",
            ),
            (
                "Subdivide out loud: count '1-e-and-a' for 16th notes while you play.",
                "This exposes rhythmic guessing. Each note lands on a syllable.",
            ),
        ],
        "success_cues": [
            "You could tap the rhythm on a table and someone would recognize it.",
            "Your notes sit in the pocket—not ahead or behind the beat, but in it.",
            "Complex rhythms feel natural; you've internalized the subdivisions.",
        ],
    },
    "tone": {
        "coaching_phrases": [
            "Tone comes from your hands more than gear. Control starts at fingertips.",
            "A beautiful tone is consistent across all strings and positions.",
            "Listen to the sustain. Good tone sings; poor tone dies quickly.",
        ],
        "drill_templates": [
            (
                "Play one note 10 times, focusing on pick angle and finger pressure.",
                "Adjust until all 10 sound identical. That's your baseline tone.",
            ),
            (
                "Play the same melody on different string sets (low, middle, high).",
                "Notice how your right hand adjusts to keep tone consistent.",
            ),
            (
                "Record a clean chord. Listen for buzzing, muting, or dead notes.",
                "Fix each problem string, then rebuild the chord with all ringing.",
            ),
        ],
        "success_cues": [
            "Every note has warmth and presence, no accidental muting or buzzing.",
            "Close your eyes and recognize your own tone—it's distinctly yours.",
            "The guitar resonates fully; sustain fades naturally, not abruptly.",
        ],
    },
}


def _select_content(skill_area: str, objective_id: str, current_level: float) -> dict[str, Any]:
    """
    Select appropriate drill content based on skill area and current level.
    Uses objective_id hash for deterministic variety (same input = same output).
    """
    library = SKILL_LIBRARY.get(skill_area, SKILL_LIBRARY["tempo"])  # fallback to tempo

    # Use objective_id hash for deterministic selection
    hash_val = sum(ord(c) for c in objective_id)

    phrase_idx = hash_val % len(library["coaching_phrases"])
    drill_idx = hash_val % len(library["drill_templates"])
    cue_idx = hash_val % len(library["success_cues"])

    return {
        "coaching_phrase": library["coaching_phrases"][phrase_idx],
        "drill_steps": list(library["drill_templates"][drill_idx]),
        "success_cue": library["success_cues"][cue_idx],
    }


def _format_drill_steps(steps: list[str], evidence: dict) -> list[str]:
    """Apply context-specific formatting to drill steps."""
    session_stats = evidence.get("session_stats", {})
    bpm = session_stats.get("tempo_bpm", 80)

    formatted = []
    for step in steps:
        formatted_step = step.format(
            bpm=int(bpm),
            half_bpm=int(bpm / 2),
        )
        formatted.append(formatted_step)
    return formatted


def _generate_drill_packs(
    teaching_objectives: list[dict[str, Any]],
    evidence: dict,
) -> list[dict[str, Any]]:
    """Generate drill packs for each teaching objective."""
    drill_packs = []

    for obj in teaching_objectives:
        objective_id = obj.get("objective_id", "unknown")
        skill_area = obj.get("skill_area", "tempo")
        current_level = obj.get("current_level", 0.5)

        content = _select_content(skill_area, objective_id, current_level)

        drill_pack = {
            "objective_id": objective_id,
            "coaching_phrase": content["coaching_phrase"],
            "drill_steps": _format_drill_steps(content["drill_steps"], evidence),
            "success_cue": content["success_cue"],
        }

        drill_packs.append(drill_pack)

    return drill_packs


def _generate_feedback(
    teaching_objectives: list[dict[str, Any]],
    evidence: dict,
) -> list[dict[str, Any]]:
    """Generate feedback items for governance compliance (evidence-cited)."""
    feedback = []

    # Primary focus area from objectives
    if teaching_objectives:
        primary = teaching_objectives[0]
        skill = primary.get("skill_area", "tempo")
        level = primary.get("current_level", 0.5)

        feedback.append(
            {
                "category": "focus_area",
                "text": f"Focus on {skill}: {primary.get('description', 'improving this skill')}",
                "evidence_refs": [{"metric": f"{skill}_level", "value": level}],
                "priority": 1,
            }
        )

    # Encouragement (always present for governance)
    feedback.append(
        {
            "category": "encouragement",
            "text": "Each drill builds muscle memory. Trust the process and feel the improvement.",
            "evidence_refs": [{"metric": "objectives_count", "value": len(teaching_objectives)}],
            "priority": 5,
        }
    )

    return feedback


def run_job(context: dict) -> dict[str, Any]:
    """
    Run the explain_drill job.

    Input: CoachContextPacket with request.teaching_objectives[]
    Output: CoachingDraft with drill_packs[]
    """
    # Governance: check for PII before processing
    ensure_no_pii_fields(context)

    request = context.get("request", {}) or {}
    evidence = context.get("evidence", {}) or {}
    teaching_objectives = request.get("teaching_objectives")

    # Validate: explain_drill requires teaching objectives from sg-coach
    if not isinstance(teaching_objectives, list) or len(teaching_objectives) == 0:
        raise ValueError(
            "explain_drill requires request.teaching_objectives[] (non-empty). "
            "This job consumes teaching objectives from sg-coach."
        )

    # Generate drill packs for each objective
    drill_packs = _generate_drill_packs(teaching_objectives, evidence)

    # Generate feedback (required by schema)
    feedback = _generate_feedback(teaching_objectives, evidence)

    # Build the draft
    draft = {
        "schema_id": "coaching_draft_v1",
        "schema_version": "v1",
        "kind": "explain_drill",
        "model": {
            "id": "groove_layer_v1",
            "runtime": "local",
        },
        "template": {
            "id": SUPPORTED_TEMPLATE_ID,
            "version": SUPPORTED_TEMPLATE_VERSION,
        },
        "feedback": feedback,
        "drill_packs": drill_packs,
    }

    # Governance: verify output
    ensure_no_pii_fields(draft)
    ensure_feedback_has_evidence(draft)

    return draft
