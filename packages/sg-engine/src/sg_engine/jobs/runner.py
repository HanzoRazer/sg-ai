# src/sg_engine/jobs/runner.py
"""
Job runner (dispatch) for sg-ai.

Strict dispatch rules:
- Dispatch is based on request.kind + template_id
- Only supported jobs run; unknowns fail (no fallback)
"""

from __future__ import annotations

from typing import Any, Dict

from sg_engine.jobs.groove_feedback import run_job as run_groove_feedback
from sg_engine.jobs.practice_summary import run_job as run_practice_summary
from sg_engine.jobs.timing_feedback import run_timing_feedback
from sg_engine.jobs.explain_drill import run_job as run_explain_drill


class UnsupportedJobError(ValueError):
    pass


def run(context: dict) -> Dict[str, Any]:
    req = context.get("request", {}) or {}
    kind = req.get("kind")
    template_id = req.get("template_id")

    if kind == "groove_feedback" and template_id == "groove_feedback":
        return run_groove_feedback(context)

    if kind == "practice_summary" and template_id == "practice_summary":
        return run_practice_summary(context)

    if kind == "timing_feedback" and template_id == "timing_feedback":
        return run_timing_feedback(context)

    if kind == "explain_drill" and template_id == "explain_drill":
        return run_explain_drill(context)

    raise UnsupportedJobError(f"Unsupported job: kind={kind!r}, template_id={template_id!r}")
