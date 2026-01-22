#!/usr/bin/env python3
"""
Run acceptance vectors against the Groove Layer.

Usage:
    python scripts/run_vectors.py
    python scripts/run_vectors.py --strict  # Fail on any mismatch
    python scripts/run_vectors.py --debug   # Verbose output
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


def load_vectors(vectors_dir: Path) -> list[tuple[Path, dict]]:
    """Load all vector files."""
    vectors = []
    for vector_file in sorted(vectors_dir.glob("*.json")):
        if vector_file.name.startswith("_"):
            continue  # Skip files starting with underscore
        content = json.loads(vector_file.read_text())
        vectors.append((vector_file, content))
    return vectors


def run_vector(vector: dict, debug: bool = False) -> dict:
    """Run a single vector and return the output."""
    context = vector.get("input", {})
    try:
        result = run_coaching_job(context)
        return {"success": True, "output": result}
    except Exception as e:
        if debug:
            import traceback
            traceback.print_exc()
        return {"success": False, "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run acceptance vectors")
    parser.add_argument("--strict", action="store_true", help="Fail on any mismatch")
    parser.add_argument("--debug", action="store_true", help="Verbose output")
    args = parser.parse_args()

    vectors_dir = REPO_ROOT / "fixtures" / "vectors"

    if not vectors_dir.exists():
        print(f"No vectors directory found at {vectors_dir}")
        print("Creating empty vectors directory...")
        vectors_dir.mkdir(parents=True, exist_ok=True)
        return 0

    vectors = load_vectors(vectors_dir)

    if not vectors:
        print("No vectors found. Add .json files to fixtures/vectors/")
        return 0

    print(f"Running {len(vectors)} vectors...")
    print()

    passed = 0
    failed = 0

    for vector_file, vector in vectors:
        name = vector_file.stem
        expected = vector.get("expected", {})

        result = run_vector(vector, debug=args.debug)

        if result["success"]:
            # Check expected output if provided
            if expected:
                actual_kind = result["output"].get("kind")
                expected_kind = expected.get("kind")
                if actual_kind != expected_kind:
                    print(f"FAIL: {name} - kind mismatch: {actual_kind} != {expected_kind}")
                    failed += 1
                    continue

            print(f"PASS: {name}")
            passed += 1
        else:
            if expected.get("should_fail"):
                print(f"PASS: {name} (expected failure)")
                passed += 1
            else:
                print(f"FAIL: {name} - {result['error']}")
                failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed")

    if args.strict and failed > 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
