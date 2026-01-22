# sg_engine — Offline AI Coach for Smart Guitar
"""
Groove Layer Intelligence engine.

Usage:
    from sg_engine import run_coaching_job
    from sg_engine.schemas import CoachContextPacket

    draft = run_coaching_job(context)
"""

from sg_engine.jobs.runner import run as run_coaching_job

__version__ = "0.1.0"
__all__ = ["run_coaching_job", "__version__"]
