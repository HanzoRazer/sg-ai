"""
SG-AI API Router.

Endpoints:
- GET  /api/status           — health + versions + hw flags
- POST /api/session/start    — start new coaching session
- POST /api/session/event    — ingest groove events
- GET  /api/session/state    — get current session state
- POST /api/session/stop     — end session
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------


class StatusResponse(BaseModel):
    """Device status response."""

    ok: bool = True
    timestamp_utc: str
    versions: dict[str, str]
    hw_flags: dict[str, Any] = Field(default_factory=dict)


class VersionResponse(BaseModel):
    """Bundle version + git provenance for OTA diagnostics."""

    bundle_version: str | None = None
    git_sha: str | None = None
    git_dirty: bool | None = None
    build_time_utc: str | None = None
    sg_engine_version: str = "0.1.0"
    manifest_found: bool = False


class SessionStartRequest(BaseModel):
    """Request to start a new session."""

    device_id: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class SessionStartResponse(BaseModel):
    """Response after starting a session."""

    session_id: UUID
    started_at: str


class SessionEventRequest(BaseModel):
    """Ingest groove/performance events."""

    session_id: UUID
    events: list[dict[str, Any]]


class SessionEventResponse(BaseModel):
    """Response after ingesting events."""

    session_id: UUID
    events_received: int
    feedback: dict[str, Any] | None = None


class SessionStateResponse(BaseModel):
    """Current session state."""

    session_id: UUID | None
    active: bool
    started_at: str | None = None
    event_count: int = 0
    latest_feedback: dict[str, Any] | None = None


class SessionStopRequest(BaseModel):
    """Request to stop a session."""

    session_id: UUID


class SessionStopResponse(BaseModel):
    """Response after stopping a session."""

    session_id: UUID
    stopped_at: str
    summary: dict[str, Any] | None = None


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Health check + version info."""
    return StatusResponse(
        ok=True,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        versions={
            "sg_engine": "0.1.0",
            "api": "v1",
        },
        hw_flags={
            "platform": "smart_guitar",
        },
    )


def _get_git_sha() -> str | None:
    """Get current git SHA (runtime fallback)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()[:12]
    except Exception:
        return None


def _load_manifest() -> dict | None:
    """Load manifest.json from bundle root (if exists)."""
    # Try common locations
    for candidate in [
        Path("/opt/sg-ai/manifest.json"),
        Path(__file__).parent.parent.parent.parent.parent / "manifest.json",
    ]:
        if candidate.exists():
            try:
                return json.loads(candidate.read_text())
            except Exception:
                pass
    return None


@router.get("/version", response_model=VersionResponse)
async def get_version():
    """Bundle version + git provenance for OTA diagnostics."""
    manifest = _load_manifest()
    
    if manifest:
        return VersionResponse(
            bundle_version=manifest.get("bundle_version"),
            git_sha=manifest.get("git_sha"),
            git_dirty=manifest.get("git_dirty"),
            build_time_utc=manifest.get("build_time_utc"),
            sg_engine_version="0.1.0",
            manifest_found=True,
        )
    
    # Fallback: runtime git SHA (dev mode)
    return VersionResponse(
        bundle_version=None,
        git_sha=_get_git_sha(),
        git_dirty=None,
        build_time_utc=None,
        sg_engine_version="0.1.0",
        manifest_found=False,
    )


@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest, request: Request):
    """Start a new coaching session."""
    store = request.app.state.session_store

    session_id = uuid4()
    started_at = datetime.now(timezone.utc).isoformat()

    store.create_session(
        session_id=session_id,
        device_id=req.device_id,
        context=req.context,
    )

    return SessionStartResponse(
        session_id=session_id,
        started_at=started_at,
    )


@router.post("/session/event", response_model=SessionEventResponse)
async def ingest_event(req: SessionEventRequest, request: Request):
    """Ingest groove/performance events."""
    store = request.app.state.session_store

    session = store.get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Add events to session
    store.add_events(req.session_id, req.events)

    # Generate feedback (placeholder — actual logic in groove_layer)
    feedback = None
    if len(req.events) > 0:
        feedback = {
            "type": "acknowledgment",
            "message": f"Received {len(req.events)} events",
        }

    return SessionEventResponse(
        session_id=req.session_id,
        events_received=len(req.events),
        feedback=feedback,
    )


@router.get("/session/state", response_model=SessionStateResponse)
async def get_session_state(request: Request):
    """Get current session state."""
    store = request.app.state.session_store

    active_session = store.get_active_session()
    if active_session is None:
        return SessionStateResponse(
            session_id=None,
            active=False,
        )

    return SessionStateResponse(
        session_id=active_session["session_id"],
        active=True,
        started_at=active_session.get("started_at"),
        event_count=len(active_session.get("events", [])),
        latest_feedback=active_session.get("latest_feedback"),
    )


@router.post("/session/stop", response_model=SessionStopResponse)
async def stop_session(req: SessionStopRequest, request: Request):
    """Stop a session."""
    store = request.app.state.session_store

    session = store.get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stopped_at = datetime.now(timezone.utc).isoformat()

    # Generate summary (placeholder — actual logic in groove_layer)
    summary = store.stop_session(req.session_id)

    return SessionStopResponse(
        session_id=req.session_id,
        stopped_at=stopped_at,
        summary=summary,
    )
