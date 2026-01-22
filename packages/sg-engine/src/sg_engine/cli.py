# src/sg_engine/cli.py
"""
sgc CLI — Smart Guitar Coach

Device commands:
  sgc run         Start the device runtime server
  sgc status      Check device/server status

Coaching commands:
  sgc run-job     Run a coaching job from CoachContextPacket
  sgc validate    Validate schemas

Exit codes (per Integration Spec v1):
- 0: success
- 1: schema validation error (input or output)
- 2: governance violation (PII detected)
- 3: model runtime error
- 4: unsupported job/template
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sg_engine.validate import SchemaValidationError, validate_json_schema
from sg_engine.governance import GovernanceViolation
from sg_engine.jobs.runner import run as run_dispatch
from sg_engine.schemas import load_schema


def _read_json(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# -----------------------------------------------------------------------------
# Device Commands
# -----------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    """Start the device runtime server."""
    from sg_engine.device_runtime import run_server

    static_dir = Path(args.static_dir) if args.static_dir else None

    print(f"[sgc] Starting device runtime on {args.host}:{args.port}")
    if static_dir:
        print(f"[sgc] Serving UI from: {static_dir}")

    try:
        run_server(
            host=args.host,
            port=args.port,
            static_dir=static_dir,
            reload=args.reload,
        )
        return 0
    except KeyboardInterrupt:
        print("\n[sgc] Shutting down...")
        return 0
    except Exception as e:
        print(f"[sgc] runtime error: {e}", file=sys.stderr)
        return 3


def cmd_status(args: argparse.Namespace) -> int:
    """Check device/server status."""
    import urllib.request
    import urllib.error

    url = f"http://{args.host}:{args.port}/api/status"

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[sgc] Status: {'OK' if data.get('ok') else 'ERROR'}")
            print(f"[sgc] Timestamp: {data.get('timestamp_utc')}")
            versions = data.get("versions", {})
            for k, v in versions.items():
                print(f"[sgc]   {k}: {v}")
            return 0
    except urllib.error.URLError as e:
        print(f"[sgc] Cannot connect to {url}: {e.reason}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[sgc] Error: {e}", file=sys.stderr)
        return 3


# -----------------------------------------------------------------------------
# Coaching Commands
# -----------------------------------------------------------------------------


def cmd_run_job(args: argparse.Namespace) -> int:
    """Run a coaching job from CoachContextPacket."""
    in_path = Path(args.input)
    out_path = Path(args.output)

    try:
        packet = _read_json(in_path)

        schema_id = packet.get("schema_id")
        if schema_id != "coach_context_packet_v1":
            raise ValueError(f"Unsupported schema_id: {schema_id!r}")

        validate_json_schema(packet, load_schema("coach_context_packet_v1.json"))
        draft = run_dispatch(packet)
        validate_json_schema(draft, load_schema("coaching_draft_v1.json"))
        _write_json(out_path, draft)
        return 0

    except SchemaValidationError as e:
        print(f"[sgc] schema validation error: {e}", file=sys.stderr)
        return 1
    except GovernanceViolation as e:
        print(f"[sgc] governance violation: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"[sgc] unsupported: {e}", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"[sgc] runtime error: {e}", file=sys.stderr)
        return 3


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate schemas."""
    try:
        if args.context:
            packet = _read_json(Path(args.context))
            validate_json_schema(packet, load_schema("coach_context_packet_v1.json"))
            print(f"[sgc] context valid: {args.context}")
        if args.draft:
            draft = _read_json(Path(args.draft))
            validate_json_schema(draft, load_schema("coaching_draft_v1.json"))
            print(f"[sgc] draft valid: {args.draft}")
        return 0
    except SchemaValidationError as e:
        print(f"[sgc] validation error: {e}", file=sys.stderr)
        return 1


# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sgc", description="Smart Guitar Coach CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Device commands
    p_run = sub.add_parser("run", help="Start the device runtime server.")
    p_run.add_argument("--host", default="0.0.0.0", help="Bind host")
    p_run.add_argument("--port", type=int, default=8000, help="HTTP port")
    p_run.add_argument("--static-dir", help="Path to sg-app/dist")
    p_run.add_argument("--reload", action="store_true", help="Auto-reload (dev)")
    p_run.set_defaults(func=cmd_run)

    p_status = sub.add_parser("status", help="Check device/server status.")
    p_status.add_argument("--host", default="127.0.0.1", help="Server host")
    p_status.add_argument("--port", type=int, default=8000, help="Server port")
    p_status.set_defaults(func=cmd_status)

    # Coaching commands
    p_job = sub.add_parser("run-job", help="Run a coaching job.")
    p_job.add_argument("--in", dest="input", required=True, help="Input JSON")
    p_job.add_argument("--out", dest="output", required=True, help="Output JSON")
    p_job.set_defaults(func=cmd_run_job)

    p_val = sub.add_parser("validate", help="Validate schemas.")
    p_val.add_argument("--context", help="CoachContextPacket JSON")
    p_val.add_argument("--draft", help="CoachingDraft JSON")
    p_val.set_defaults(func=cmd_validate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
