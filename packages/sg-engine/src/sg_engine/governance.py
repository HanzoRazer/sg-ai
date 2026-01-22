# src/sg_engine/governance.py
"""
Governance enforcement helpers for Smart Guitar AI Coach.

Strict rules:
- No PII fields anywhere in input/output (player_id, account_id, email, etc.)
- No raw user content references (audio_url, recording_path)
- Every feedback must cite session evidence
- Latency budget awareness (soft constraint, enforced in CI)

These checks are intentionally conservative. If in doubt, fail.
"""

from __future__ import annotations

from typing import Any, Set


class GovernanceViolation(ValueError):
    """Raised when governance rules are violated."""
    pass


# PII and forbidden fields - these must NEVER appear in schemas/data
FORBIDDEN_PII_FIELDS: Set[str] = {
    "player_id",
    "account_id",
    "user_id",
    "email",
    "phone",
    "address",
    "name",
    "full_name",
    "first_name",
    "last_name",
    "date_of_birth",
    "ssn",
    "credit_card",
    "password",
}

# Fields that could leak raw user content
FORBIDDEN_CONTENT_FIELDS: Set[str] = {
    "audio_url",
    "audio_blob",
    "recording_url",
    "recording_path",
    "video_url",
    "image_url",
    "raw_midi",
}


def ensure_no_pii_fields(obj: Any, path: str = "") -> None:
    """
    Deep-scan for PII fields. Raise GovernanceViolation if found.
    """
    forbidden = FORBIDDEN_PII_FIELDS | FORBIDDEN_CONTENT_FIELDS

    def walk(x: Any, p: str) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                key_lower = k.lower() if isinstance(k, str) else ""
                if key_lower in forbidden:
                    raise GovernanceViolation(f"Forbidden PII field '{k}' at {p or '$'}")
                walk(v, f"{p}.{k}" if p else f"$.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{p}[{i}]")

    walk(obj, path)


def ensure_feedback_has_evidence(draft: dict) -> None:
    """
    Ensure every feedback item cites session evidence.
    """
    feedback = draft.get("feedback")
    if not isinstance(feedback, list) or len(feedback) == 0:
        raise GovernanceViolation("Output must include non-empty 'feedback' array")

    for i, f in enumerate(feedback):
        if not isinstance(f, dict):
            raise GovernanceViolation(f"feedback[{i}] must be an object")
        evidence = f.get("evidence_refs")
        if not isinstance(evidence, list) or len(evidence) == 0:
            raise GovernanceViolation(f"feedback[{i}] must include non-empty evidence_refs[]")


def ensure_no_scoring_language(draft: dict) -> None:
    """
    Ensure feedback doesn't use absolute scoring language.
    Coaching should be encouraging, not judgmental.
    """
    forbidden_words = {"terrible", "awful", "horrible", "failed", "failure", "wrong"}

    feedback = draft.get("feedback", [])
    for i, f in enumerate(feedback):
        text = f.get("text", "").lower()
        for word in forbidden_words:
            if word in text:
                raise GovernanceViolation(
                    f"feedback[{i}] contains discouraged language: '{word}'. "
                    "Use constructive feedback instead."
                )


def check_governance(context: dict, draft: dict) -> None:
    """
    Run all governance checks on context and draft.
    """
    # Check input for PII
    ensure_no_pii_fields(context, "context")

    # Check output for PII
    ensure_no_pii_fields(draft, "draft")

    # Check output structure
    ensure_feedback_has_evidence(draft)

    # Check language
    ensure_no_scoring_language(draft)
