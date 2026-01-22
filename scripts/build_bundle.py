#!/usr/bin/env python3
"""
Build deterministic device bundle for Smart Guitar AI Coach.

Usage:
    python scripts/build_bundle.py --version 1.0.0
    python scripts/build_bundle.py --version 1.0.0 --output dist/custom.zip
    python scripts/build_bundle.py --version 1.0.0 --include-ui

Bundle contents:
- packages/sg-engine/     (Python source)
- packages/sg-app/dist/   (UI build, if --include-ui)
- contracts/              (JSON schemas)
- deploy/                 (systemd, README)
- pyproject.toml          (for uv sync)
- uv.lock                 (locked dependencies)
- manifest.json           (bundle metadata)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def get_git_sha() -> str:
    """Get current git SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:12]
    except Exception:
        return "unknown"


def get_git_dirty() -> bool:
    """Check if workspace is dirty."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True


def build_manifest(version: str, include_ui: bool) -> dict:
    """Build manifest.json content per device_bundle_manifest_v1 schema."""
    return {
        "schema_id": "device_bundle_manifest_v1",
        "schema_version": "1.0",
        "bundle_version": version,
        "git_sha": get_git_sha(),
        "git_dirty": get_git_dirty(),
        "build_time_utc": datetime.now(timezone.utc).isoformat(),
        "target_platform": "smart_guitar",
        "components": {
            "sg_engine": version,
            "sg_app": version if include_ui else None,
        },
        "entrypoint": {
            "module": "sg_engine.device_runtime",
            "port": 8000,
        },
        "install": {
            "requires_uv_sync": True,
            "python_version": "3.11",
        },
        "ui": {
            "included": include_ui,
            "mount_path": "/",
        },
    }


def collect_files(repo_root: Path, include_ui: bool) -> list[tuple[str, Path]]:
    """Collect files to include in bundle."""
    files = []

    # Python package source
    sg_engine_src = repo_root / "packages" / "sg-engine" / "src"
    if sg_engine_src.exists():
        for py_file in sg_engine_src.rglob("*.py"):
            rel_path = py_file.relative_to(repo_root)
            files.append((str(rel_path).replace("\\", "/"), py_file))
        for json_file in sg_engine_src.rglob("*.json"):
            rel_path = json_file.relative_to(repo_root)
            files.append((str(rel_path).replace("\\", "/"), json_file))

    # pyproject.toml (for uv sync)
    pyproject = repo_root / "packages" / "sg-engine" / "pyproject.toml"
    if pyproject.exists():
        files.append(("packages/sg-engine/pyproject.toml", pyproject))

    # uv.lock (if exists)
    uv_lock = repo_root / "packages" / "sg-engine" / "uv.lock"
    if uv_lock.exists():
        files.append(("packages/sg-engine/uv.lock", uv_lock))

    # Contracts
    contracts = repo_root / "contracts"
    if contracts.exists():
        for json_file in contracts.glob("*.json"):
            files.append((f"contracts/{json_file.name}", json_file))

    # Deploy files
    deploy = repo_root / "deploy"
    if deploy.exists():
        for f in deploy.rglob("*"):
            if f.is_file():
                rel_path = f.relative_to(repo_root)
                files.append((str(rel_path).replace("\\", "/"), f))

    # UI build (if requested and exists)
    if include_ui:
        sg_app_dist = repo_root / "packages" / "sg-app" / "dist"
        if sg_app_dist.exists():
            for f in sg_app_dist.rglob("*"):
                if f.is_file():
                    rel_path = f.relative_to(repo_root)
                    files.append((str(rel_path).replace("\\", "/"), f))
        else:
            print("WARNING: --include-ui specified but packages/sg-app/dist not found")

    return sorted(files, key=lambda x: x[0])


def create_bundle(
    output_path: Path,
    version: str,
    repo_root: Path,
    include_ui: bool,
) -> str:
    """Create the bundle zip file. Returns SHA256 hash."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = collect_files(repo_root, include_ui)
    manifest = build_manifest(version, include_ui)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest_json = json.dumps(manifest, indent=2, sort_keys=True)
        zf.writestr("manifest.json", manifest_json)

        for arc_name, file_path in files:
            zf.write(file_path, arc_name)

    sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return sha256


def main() -> int:
    parser = argparse.ArgumentParser(description="Build device bundle")
    parser.add_argument("--version", required=True, help="Version string (semver)")
    parser.add_argument("--output", default="dist/device_bundle.zip", help="Output path")
    parser.add_argument("--include-ui", action="store_true", help="Include sg-app/dist")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    output_path = repo_root / args.output

    if get_git_dirty():
        print("WARNING: Workspace is dirty. Bundle may not be reproducible.")

    print(f"Building bundle version {args.version}...")
    print(f"  Include UI: {args.include_ui}")

    sha256 = create_bundle(output_path, args.version, repo_root, args.include_ui)

    print(f"Bundle created: {output_path}")
    print(f"SHA256: {sha256}")

    hash_path = output_path.with_suffix(".zip.sha256")
    hash_path.write_text(f"{sha256}  {output_path.name}\n")
    print(f"Hash file: {hash_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
