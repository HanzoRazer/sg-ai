# tests/test_groove_adapter.py
"""
Tests for groove adapter — sg-spec to sg-ai context transformation.
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from sg_engine.adapters.groove_adapter import (
    groove_profile_to_metrics,
    coach_evaluation_to_context,
    session_record_to_stats,
    build_groove_feedback_context,
    build_practice_summary_context,
)


def _mock_groove_profile():
    """Create a mock GrooveProfileV1."""
    profile = MagicMock()

    # timing_bias
    profile.timing_bias.mean_offset_ms = 5.0
    profile.timing_bias.stddev_ms = 2.0
    profile.timing_bias.direction = "ahead"
    profile.timing_bias.confidence = 0.85

    # tempo_stability
    profile.tempo_stability.supported_bpm_range = (80, 140)
    profile.tempo_stability.drift_slope = 0.01
    profile.tempo_stability.fatigue_sensitivity = 0.3
    profile.tempo_stability.confidence = 0.9

    # subdivision_fidelity
    profile.subdivision_fidelity.supported = ["quarter", "eighth", "sixteenth"]
    profile.subdivision_fidelity.unstable = ["triplet"]
    profile.subdivision_fidelity.swing_tolerance = 0.7
    profile.subdivision_fidelity.confidence = 0.88

    # error_recovery
    profile.error_recovery.mean_recovery_beats = 2.5
    profile.error_recovery.panic_probability = 0.1
    profile.error_recovery.self_correction_rate = 0.8

    # groove_elasticity
    profile.groove_elasticity.microtiming_flex_ms = 15.0
    profile.groove_elasticity.lock_threshold = 0.75
    profile.groove_elasticity.push_pull_balance = "balanced"

    # confidence_band
    profile.confidence_band.lower = 0.7
    profile.confidence_band.upper = 0.95

    # evidence_window
    profile.evidence_window.sessions = 10
    profile.evidence_window.events = 5000

    return profile


def _mock_session_record():
    """Create a mock SessionRecord."""
    session = MagicMock()
    session.session_id = uuid4()
    session.duration_s = 600

    # performance
    session.performance.notes_played = 450
    session.performance.notes_expected = 500
    session.performance.notes_dropped = 50
    session.performance.bars_played = 32
    session.performance.timing_error_ms.mean = 15.5
    session.performance.timing_error_ms.std = 8.2
    session.performance.timing_error_ms.max = 45.0

    # events
    session.events.late_drops = 5
    session.events.panic_triggered = False

    # program_ref
    session.program_ref.name = "salsa_minor_dm"
    session.program_ref.type.value = "ztprog"

    # timing
    session.timing.bpm = 110
    session.timing.grid = 16

    return session


def _mock_coach_evaluation():
    """Create a mock CoachEvaluation."""
    evaluation = MagicMock()
    evaluation.session_id = uuid4()
    evaluation.confidence = 0.87

    # findings
    finding1 = MagicMock()
    finding1.type = "timing"
    finding1.severity.value = "primary"
    finding1.interpretation = "Late on step 7"
    finding1.evidence.step = 7
    finding1.evidence.mean_error_ms = 31.8

    finding2 = MagicMock()
    finding2.type = "consistency"
    finding2.severity.value = "secondary"
    finding2.interpretation = "Notes dropped"
    finding2.evidence.step = None
    finding2.evidence.mean_error_ms = None

    evaluation.findings = [finding1, finding2]
    evaluation.strengths = ["Stable tempo", "Good dynamics"]
    evaluation.weaknesses = ["Off-beat timing"]
    evaluation.focus_recommendation.concept = "clave_alignment"
    evaluation.focus_recommendation.reason = "Timing concentrated on clave off-beats"

    return evaluation


class TestGrooveProfileToMetrics:
    """Tests for groove_profile_to_metrics adapter."""

    def test_extracts_tempo_stability(self):
        """Extracts tempo stability from profile."""
        profile = _mock_groove_profile()
        metrics = groove_profile_to_metrics(profile)

        assert metrics["tempo_stability"] == 0.9

    def test_calculates_beat_accuracy(self):
        """Calculates beat accuracy from timing offset."""
        profile = _mock_groove_profile()
        metrics = groove_profile_to_metrics(profile)

        # offset of 5ms should give high accuracy
        assert metrics["beat_accuracy"] == 0.9  # 1 - (5/50)

    def test_extracts_dynamics_range(self):
        """Extracts dynamics range from elasticity."""
        profile = _mock_groove_profile()
        metrics = groove_profile_to_metrics(profile)

        assert metrics["dynamics_range"] == 0.75

    def test_extracts_articulation_clarity(self):
        """Extracts articulation clarity from subdivision fidelity."""
        profile = _mock_groove_profile()
        metrics = groove_profile_to_metrics(profile)

        assert metrics["articulation_clarity"] == 0.88

    def test_includes_profile_context(self):
        """Includes additional profile context."""
        profile = _mock_groove_profile()
        metrics = groove_profile_to_metrics(profile)

        assert "_profile_context" in metrics
        assert metrics["_profile_context"]["timing_direction"] == "ahead"
        assert metrics["_profile_context"]["push_pull_balance"] == "balanced"

    def test_includes_confidence_band(self):
        """Includes confidence band for uncertainty."""
        profile = _mock_groove_profile()
        metrics = groove_profile_to_metrics(profile)

        assert "_confidence" in metrics
        assert metrics["_confidence"]["lower"] == 0.7
        assert metrics["_confidence"]["upper"] == 0.95

    def test_includes_evidence_window(self):
        """Includes evidence window for data quality."""
        profile = _mock_groove_profile()
        metrics = groove_profile_to_metrics(profile)

        assert "_evidence" in metrics
        assert metrics["_evidence"]["sessions"] == 10
        assert metrics["_evidence"]["events"] == 5000


class TestSessionRecordToStats:
    """Tests for session_record_to_stats adapter."""

    def test_extracts_duration(self):
        """Extracts session duration."""
        session = _mock_session_record()
        stats = session_record_to_stats(session)

        assert stats["duration_seconds"] == 600

    def test_extracts_notes_played(self):
        """Extracts notes played count."""
        session = _mock_session_record()
        stats = session_record_to_stats(session)

        assert stats["notes_played"] == 450
        assert stats["notes_expected"] == 500
        assert stats["notes_dropped"] == 50

    def test_extracts_timing_stats(self):
        """Extracts timing error statistics."""
        session = _mock_session_record()
        stats = session_record_to_stats(session)

        assert stats["timing_error_mean_ms"] == 15.5
        assert stats["timing_error_std_ms"] == 8.2
        assert stats["timing_error_max_ms"] == 45.0

    def test_extracts_events(self):
        """Extracts event counts."""
        session = _mock_session_record()
        stats = session_record_to_stats(session)

        assert stats["late_drops"] == 5
        assert stats["panic_triggered"] is False

    def test_extracts_program_info(self):
        """Extracts program reference."""
        session = _mock_session_record()
        stats = session_record_to_stats(session)

        assert stats["program_name"] == "salsa_minor_dm"
        assert stats["program_type"] == "ztprog"

    def test_extracts_timing_config(self):
        """Extracts timing configuration."""
        session = _mock_session_record()
        stats = session_record_to_stats(session)

        assert stats["bpm"] == 110
        assert stats["grid"] == 16


class TestCoachEvaluationToContext:
    """Tests for coach_evaluation_to_context adapter."""

    def test_extracts_findings(self):
        """Extracts coach findings."""
        evaluation = _mock_coach_evaluation()
        context = coach_evaluation_to_context(evaluation)

        assert len(context["coach_findings"]) == 2
        assert context["coach_findings"][0]["type"] == "timing"
        assert context["coach_findings"][0]["step"] == 7

    def test_extracts_strengths_weaknesses(self):
        """Extracts strengths and weaknesses."""
        evaluation = _mock_coach_evaluation()
        context = coach_evaluation_to_context(evaluation)

        assert "Stable tempo" in context["strengths"]
        assert "Off-beat timing" in context["weaknesses"]

    def test_extracts_focus_recommendation(self):
        """Extracts focus recommendation."""
        evaluation = _mock_coach_evaluation()
        context = coach_evaluation_to_context(evaluation)

        assert context["focus_recommendation"]["concept"] == "clave_alignment"

    def test_extracts_confidence(self):
        """Extracts confidence score."""
        evaluation = _mock_coach_evaluation()
        context = coach_evaluation_to_context(evaluation)

        assert context["confidence"] == 0.87


class TestBuildGrooveFeedbackContext:
    """Tests for build_groove_feedback_context."""

    def test_builds_complete_context(self):
        """Builds complete context from profile and session."""
        profile = _mock_groove_profile()
        session = _mock_session_record()

        context = build_groove_feedback_context(profile, session)

        assert "session_id" in context
        assert "groove_metrics" in context
        assert "session_stats" in context

    def test_uses_session_id_override(self):
        """Uses provided session ID override."""
        profile = _mock_groove_profile()
        session = _mock_session_record()

        context = build_groove_feedback_context(profile, session, session_id="custom-123")

        assert context["session_id"] == "custom-123"


class TestBuildPracticeSummaryContext:
    """Tests for build_practice_summary_context."""

    def test_builds_basic_context(self):
        """Builds basic context from session."""
        session = _mock_session_record()

        context = build_practice_summary_context(session)

        assert "session_id" in context
        assert "session_stats" in context
        assert "session_history" in context

    def test_includes_evaluation_when_provided(self):
        """Includes coach context when evaluation provided."""
        session = _mock_session_record()
        evaluation = _mock_coach_evaluation()

        context = build_practice_summary_context(session, evaluation=evaluation)

        assert "coach_context" in context
        assert "coach_findings" in context["coach_context"]

    def test_includes_history_when_provided(self):
        """Includes session history when provided."""
        session = _mock_session_record()
        history = [
            {"duration_seconds": 300, "completed": True},
            {"duration_seconds": 450, "completed": True},
        ]

        context = build_practice_summary_context(session, session_history=history)

        assert len(context["session_history"]) == 2
