#!/usr/bin/env python3
"""
Check that golden outputs match current behavior.

Usage:
    python scripts/check_goldens.py
    python scripts/check_goldens.py --update  # Update goldens to match current output
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add sg-engine to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "packages" / "sg-engine" / "src"))

from sg_engine import run_coaching_job


def main() -> int:
    parser = argparse.ArgumentParser(description="Check golden outputs")
    parser.add_argument("--update", action="store_true", help="Update goldens")
    args = parser.parse_args()

    vectors_dir = REPO_ROOT / "fixtures" / "vectors"
    goldens_dir = REPO_ROOT / "fixtures" / "goldens"

    if not vectors_dir.exists():
        print("No vectors directory. Nothing to check.")
        return 0

    goldens_dir.mkdir(parents=True, exist_ok=True)

    mismatches = 0

    for vector_file in sorted(vectors_dir.glob("*.json")):
        if vector_file.name.startswith("_"):
            continue

        name = vector_file.stem
        golden_file = goldens_dir / f"{name}.golden.json"

        vector = json.loads(vector_file.read_text())
        context = vector.get("input", {})

        try:
            result = run_coaching_job(context)
        except Exception as e:
            print(f"ERROR: {name} - {e}")
            mismatches += 1
            continue

        if args.update:
            golden_file.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            print(f"UPDATED: {name}")
        elif golden_file.exists():
            golden = json.loads(golden_file.read_text())
            if result != golden:
                print(f"MISMATCH: {name}")
                mismatches += 1
            else:
                print(f"MATCH: {name}")
        else:
            print(f"NO GOLDEN: {name} (run with --update to create)")
            mismatches += 1

    if mismatches > 0 and not args.update:
        print(f"\n{mismatches} mismatches found. Run with --update to regenerate goldens.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
