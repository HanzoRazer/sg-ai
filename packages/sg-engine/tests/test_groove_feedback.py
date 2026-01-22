"""Test groove feedback job."""

from __future__ import annotations

from sg_engine.jobs.groove_feedback import run_groove_feedback


def test_groove_feedback_basic():
    """Test basic groove feedback generation."""
    context = {
        "schema_id": "coach_context_packet_v1",
        "session_id": "test-session-001",
        "device_id": "sg-dev-001",
        "timestamp_utc": "2026-01-21T10:00:00Z",
        "groove_metrics": {
            "tempo_stability": 0.85,
            "beat_accuracy": 0.90,
            "dynamics_range": 0.70,
            "articulation_clarity": 0.80,
        },
        "session_stats": {
            "duration_seconds": 300,
            "notes_played": 150,
            "tempo_bpm": 120,
        },
    }

    draft = run_groove_feedback(context)

    assert draft["schema_id"] == "coaching_draft_v1"
    assert draft["session_id"] == context["session_id"]
    assert "feedback" in draft
    assert isinstance(draft["feedback"], list)
    assert "groove_score" in draft
    assert 0 <= draft["groove_score"]["value"] <= 100


def test_groove_feedback_high_stability():
    """Test feedback for high tempo stability."""
    context = {
        "schema_id": "coach_context_packet_v1",
        "session_id": "test-session-002",
        "device_id": "sg-dev-001",
        "timestamp_utc": "2026-01-21T10:00:00Z",
        "groove_metrics": {
            "tempo_stability": 0.95,
            "beat_accuracy": 0.92,
            "dynamics_range": 0.88,
            "articulation_clarity": 0.90,
        },
        "session_stats": {
            "duration_seconds": 600,
            "notes_played": 300,
            "tempo_bpm": 100,
        },
    }

    draft = run_groove_feedback(context)

    # High stability should produce strength feedback
    strengths = [f for f in draft["feedback"] if f["category"] == "strength"]
    assert len(strengths) > 0


def test_groove_feedback_low_dynamics():
    """Test feedback for low dynamics range."""
    context = {
        "schema_id": "coach_context_packet_v1",
        "session_id": "test-session-003",
        "device_id": "sg-dev-001",
        "timestamp_utc": "2026-01-21T10:00:00Z",
        "groove_metrics": {
            "tempo_stability": 0.80,
            "beat_accuracy": 0.85,
            "dynamics_range": 0.40,
            "articulation_clarity": 0.75,
        },
        "session_stats": {
            "duration_seconds": 300,
            "notes_played": 100,
            "tempo_bpm": 80,
        },
    }

    draft = run_groove_feedback(context)

    # Low dynamics should produce focus area feedback
    focus_areas = [f for f in draft["feedback"] if f["category"] == "focus_area"]
    assert len(focus_areas) > 0
