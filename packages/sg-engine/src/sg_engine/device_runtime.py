"""
Device Runtime — FastAPI server for Smart Guitar AI Coach.

Orchestration layer only:
- Mounts API router(s)
- Mounts static UI (sg-app/dist)
- Bootstraps session store
- Starts uvicorn

Actual logic lives in sg_engine/session/* and sg_engine/groove_layer/*.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api import router as api_router
from .session.store import SessionStore

# Global session store (in-memory, device-local)
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get the global session store."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    store = get_session_store()
    app.state.session_store = store
    yield
    # Shutdown
    pass


def create_app(
    *,
    static_dir: Path | None = None,
    debug: bool = False,
) -> FastAPI:
    """
    Create the FastAPI application.

    Args:
        static_dir: Path to sg-app/dist for static UI. If None, UI not mounted.
        debug: Enable debug mode.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title="SG-AI Device Runtime",
        description="Smart Guitar AI Coach API",
        version="0.1.0",
        debug=debug,
        lifespan=lifespan,
    )

    # Mount API router
    app.include_router(api_router, prefix="/api")

    # Mount static UI if directory exists
    if static_dir and static_dir.exists():
        # Serve static files
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        # SPA fallback: serve index.html for all other routes
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """SPA fallback — serve index.html for client-side routing."""
            index_path = static_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return {"error": "UI not found"}

        @app.get("/")
        async def serve_root():
            """Serve root index.html."""
            index_path = static_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return {"error": "UI not found"}

    return app


def run_server(
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
    static_dir: Path | None = None,
    reload: bool = False,
):
    """
    Run the device runtime server.

    Args:
        host: Bind host (0.0.0.0 for all interfaces).
        port: HTTP port.
        static_dir: Path to sg-app/dist.
        reload: Enable auto-reload (dev only).
    """
    import uvicorn

    # Resolve static dir
    if static_dir is None:
        # Try default location relative to package
        default_static = Path(__file__).parent.parent.parent.parent / "sg-app" / "dist"
        if default_static.exists():
            static_dir = default_static

    app = create_app(static_dir=static_dir, debug=reload)

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
    )


def main():
    """CLI entrypoint for python -m sg_engine.device_runtime."""
    import argparse

    parser = argparse.ArgumentParser(description="SG-AI Device Runtime")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    parser.add_argument("--static-dir", type=Path, help="Path to sg-app/dist")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    run_server(
        host=args.host,
        port=args.port,
        static_dir=args.static_dir,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
