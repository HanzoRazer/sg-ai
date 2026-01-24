# tests/test_timing_feedback.py
"""
Tests for timing_feedback job — "Why Am I Off?"
"""

import pytest

from sg_engine.jobs.timing_feedback import (
    step_to_position,
    is_clave_hit,
    classify_error,
    analyze_timing_issues,
    generate_explanation,
    suggest_exercises,
    run_timing_feedback,
    why_am_i_off,
)


# =============================================================================
# Step Position Mapping Tests
# =============================================================================

class TestStepToPosition:
    """Tests for musical position mapping."""

    def test_beat_1(self):
        """Step 0 is beat 1."""
        pos = step_to_position(0, grid=16)
        assert pos["short"] == "1"
        assert "beat 1" in pos["medium"]

    def test_and_of_2(self):
        """Step 6 is the 'and' of 2."""
        pos = step_to_position(6, grid=16)
        assert pos["short"] == "2&"
        assert "and" in pos["medium"].lower()
        assert "2" in pos["medium"]

    def test_backbeat(self):
        """Step 4 is beat 2 (backbeat)."""
        pos = step_to_position(4, grid=16)
        assert pos["short"] == "2"
        assert "beat 2" in pos["medium"]

    def test_pickup(self):
        """Step 14 is the 'and' of 4 (common pickup)."""
        pos = step_to_position(14, grid=16)
        assert pos["short"] == "4&"
        assert "and" in pos["medium"].lower()

    def test_wraps_at_grid(self):
        """Steps wrap at grid boundary."""
        pos_0 = step_to_position(0, grid=16)
        pos_16 = step_to_position(16, grid=16)
        assert pos_0["short"] == pos_16["short"]

    def test_all_16_steps_have_positions(self):
        """All 16 steps have valid positions."""
        for step in range(16):
            pos = step_to_position(step, grid=16)
            assert "short" in pos
            assert "medium" in pos
            assert "long" in pos
            assert len(pos["short"]) <= 3


class TestIsClaveHit:
    """Tests for clave hit detection."""

    def test_son_2_3_hits(self):
        """son_2_3 clave has correct hit steps."""
        hits = [0, 3, 6, 10, 12]
        for step in range(16):
            expected = step in hits
            assert is_clave_hit(step, "son_2_3") == expected, f"step {step}"

    def test_unknown_clave_returns_false(self):
        """Unknown clave pattern returns False."""
        assert is_clave_hit(0, "unknown_clave") is False


# =============================================================================
# Error Classification Tests
# =============================================================================

class TestClassifyError:
    """Tests for timing error classification."""

    def test_late(self):
        """Positive error above threshold is late."""
        assert classify_error(25.0, threshold_ms=15.0) == "late"

    def test_early(self):
        """Negative error below threshold is early."""
        assert classify_error(-25.0, threshold_ms=15.0) == "early"

    def test_on_time(self):
        """Error within threshold is on_time."""
        assert classify_error(10.0, threshold_ms=15.0) == "on_time"
        assert classify_error(-10.0, threshold_ms=15.0) == "on_time"

    def test_boundary(self):
        """Exactly at threshold is on_time."""
        assert classify_error(15.0, threshold_ms=15.0) == "on_time"


# =============================================================================
# Timing Issue Analysis Tests
# =============================================================================

class TestAnalyzeTimingIssues:
    """Tests for timing issue analysis."""

    def test_identifies_late_step(self):
        """Identifies a step that's consistently late."""
        error_by_step = {"6": 35.0, "0": 5.0}
        issues = analyze_timing_issues(error_by_step)

        assert len(issues) == 1
        assert issues[0]["step"] == 6
        assert issues[0]["direction"] == "late"
        assert issues[0]["abs_error_ms"] == 35.0

    def test_identifies_early_step(self):
        """Identifies a step that's consistently early."""
        error_by_step = {"4": -30.0}
        issues = analyze_timing_issues(error_by_step)

        assert len(issues) == 1
        assert issues[0]["direction"] == "early"

    def test_clave_hits_have_higher_severity(self):
        """Clave hit errors have higher severity."""
        # Step 6 is a clave hit, step 5 is not
        error_by_step = {"5": 30.0, "6": 30.0}
        issues = analyze_timing_issues(error_by_step, clave="son_2_3")

        # Both have same error, but step 6 (clave) should be first
        assert issues[0]["step"] == 6
        assert issues[0]["on_clave"] is True
        assert issues[1]["on_clave"] is False

    def test_sorted_by_severity(self):
        """Issues are sorted by severity (worst first)."""
        error_by_step = {"0": 25.0, "6": 40.0, "4": 30.0}
        issues = analyze_timing_issues(error_by_step)

        # Step 6 has highest error AND is clave hit
        assert issues[0]["step"] == 6

    def test_ignores_small_errors(self):
        """Errors below threshold are not flagged."""
        error_by_step = {"0": 10.0, "4": 15.0}
        issues = analyze_timing_issues(error_by_step, threshold_ms=20.0)

        assert len(issues) == 0

    def test_empty_input(self):
        """Empty error_by_step returns empty list."""
        issues = analyze_timing_issues({})
        assert issues == []

    def test_includes_position_info(self):
        """Issues include position information."""
        error_by_step = {"6": 30.0}
        issues = analyze_timing_issues(error_by_step)

        assert "position" in issues[0]
        assert issues[0]["position"]["short"] == "2&"


# =============================================================================
# Explanation Generation Tests
# =============================================================================

class TestGenerateExplanation:
    """Tests for human-readable explanation generation."""

    def test_no_issues_returns_positive(self):
        """No issues gives positive feedback."""
        explanation = generate_explanation([])
        assert "solid" in explanation.lower() or "no" in explanation.lower()

    def test_single_issue_explained(self):
        """Single issue gets full explanation."""
        issues = [{
            "step": 6,
            "error_ms": 35.0,
            "abs_error_ms": 35.0,
            "direction": "late",
            "position": {"short": "2&", "medium": "the 'and' of 2", "long": ""},
            "on_clave": True,
            "severity": 52.5,
        }]
        explanation = generate_explanation(issues)

        assert "and" in explanation.lower() or "2" in explanation
        assert "late" in explanation.lower() or "dragging" in explanation.lower()

    def test_multiple_issues_listed(self):
        """Multiple issues are listed with numbers."""
        issues = [
            {"step": 6, "error_ms": 35.0, "abs_error_ms": 35.0, "direction": "late",
             "position": {"short": "2&", "medium": "the 'and' of 2", "long": ""}, "on_clave": True, "severity": 52.5},
            {"step": 4, "error_ms": 25.0, "abs_error_ms": 25.0, "direction": "late",
             "position": {"short": "2", "medium": "beat 2", "long": ""}, "on_clave": False, "severity": 25.0},
        ]
        explanation = generate_explanation(issues)

        assert "1." in explanation
        assert "2." in explanation

    def test_pattern_observation_for_consistent_late(self):
        """Observes pattern when all issues are late."""
        issues = [
            {"step": 6, "error_ms": 35.0, "abs_error_ms": 35.0, "direction": "late",
             "position": {"short": "2&", "medium": "the 'and' of 2", "long": ""}, "on_clave": True, "severity": 52.5},
            {"step": 4, "error_ms": 25.0, "abs_error_ms": 25.0, "direction": "late",
             "position": {"short": "2", "medium": "beat 2", "long": ""}, "on_clave": False, "severity": 25.0},
        ]
        explanation = generate_explanation(issues)

        assert "behind" in explanation.lower() or "consistently" in explanation.lower()


# =============================================================================
# Exercise Suggestion Tests
# =============================================================================

class TestSuggestExercises:
    """Tests for exercise suggestions."""

    def test_no_issues_gives_maintenance(self):
        """No issues suggests maintenance practice."""
        exercises = suggest_exercises([])

        assert len(exercises) == 1
        assert "maintenance" in exercises[0]["title"].lower()

    def test_step_specific_exercise(self):
        """Known problem steps get specific exercises."""
        issues = [{
            "step": 6,  # and-of-2, has specific exercise
            "error_ms": 35.0, "abs_error_ms": 35.0, "direction": "late",
            "position": {"short": "2&", "medium": "the 'and' of 2", "long": ""},
            "on_clave": True, "severity": 52.5,
        }]
        exercises = suggest_exercises(issues)

        assert len(exercises) >= 1
        # Should get the backbeat push exercise
        assert any("backbeat" in ex["title"].lower() or "push" in ex["title"].lower()
                   for ex in exercises)

    def test_direction_based_exercise(self):
        """Generic late/early issues get direction exercises."""
        issues = [{
            "step": 9,  # no specific exercise for this step
            "error_ms": 35.0, "abs_error_ms": 35.0, "direction": "late",
            "position": {"short": "3e", "medium": "the 'e' of 3", "long": ""},
            "on_clave": False, "severity": 35.0,
        }]
        exercises = suggest_exercises(issues)

        assert len(exercises) >= 1
        # Should get "think ahead" for late issues
        assert any("ahead" in ex["title"].lower() or "ahead" in ex["description"].lower()
                   for ex in exercises)

    def test_max_exercises_respected(self):
        """Doesn't return more than max_exercises."""
        issues = [
            {"step": i, "error_ms": 30.0, "abs_error_ms": 30.0, "direction": "late",
             "position": {"short": str(i), "medium": f"step {i}", "long": ""},
             "on_clave": False, "severity": 30.0}
            for i in range(10)
        ]
        exercises = suggest_exercises(issues, max_exercises=2)

        assert len(exercises) <= 2


# =============================================================================
# Main Entry Point Tests
# =============================================================================

class TestRunTimingFeedback:
    """Tests for run_timing_feedback main entry point."""

    def test_returns_correct_structure(self):
        """Returns dict with required keys."""
        context = {
            "error_by_step": {"6": 35.0},
            "grid": 16,
            "clave": "son_2_3",
        }
        result = run_timing_feedback(context)

        assert result["kind"] == "timing_feedback"
        assert "explanation" in result
        assert "issues" in result
        assert "exercises" in result
        assert "summary" in result

    def test_includes_timing_stats_if_provided(self):
        """Includes timing stats when provided."""
        context = {
            "error_by_step": {"6": 35.0},
            "timing_error_ms": {"mean": 20.0, "std": 8.0, "max": 45.0},
        }
        result = run_timing_feedback(context)

        assert "timing_stats" in result
        assert result["timing_stats"]["mean_ms"] == 20.0

    def test_handles_empty_input(self):
        """Handles empty error_by_step gracefully."""
        result = run_timing_feedback({"error_by_step": {}})

        assert result["kind"] == "timing_feedback"
        assert "solid" in result["explanation"].lower() or "on point" in result["summary"].lower()


class TestWhyAmIOff:
    """Tests for the convenience function."""

    def test_returns_string(self):
        """Returns a string explanation."""
        error_by_step = {"6": 35.0}
        result = why_am_i_off(error_by_step)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_exercise(self):
        """Includes exercise suggestion in output."""
        error_by_step = {"6": 35.0}
        result = why_am_i_off(error_by_step)

        assert "try" in result.lower()

    def test_good_timing_returns_positive(self):
        """Good timing gets positive response."""
        error_by_step = {"0": 5.0, "4": 8.0}  # All within threshold
        result = why_am_i_off(error_by_step)

        assert "solid" in result.lower() or "good" in result.lower()
