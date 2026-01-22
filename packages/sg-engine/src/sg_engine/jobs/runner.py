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


class UnsupportedJobError(ValueError):
    pass


def run(context: dict) -> Dict[str, Any]:
    req = context.get("request", {}) or {}
    kind = req.get("kind")
    template_id = req.get("template_id")

    if kind == "groove_feedback" and template_id == "groove_feedback":
        return run_groove_feedback(context)

    # Future jobs
    # if kind == "practice_summary" and template_id == "practice_summary":
    #     return run_practice_summary(context)

    raise UnsupportedJobError(f"Unsupported job: kind={kind!r}, template_id={template_id!r}")
