#!/usr/bin/env python3
"""Download eval datasets to evals/datasets/.

Datasets are gitignored (can be large). Use this script to fetch them.

Usage:
    python -m evals.download [dataset_name ...]
    python -m evals.download --list
    python -m evals.download --all

Examples:
    python -m evals.download locomo10
    python -m evals.download locomo10 longmemeval_oracle
    python -m evals.download --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request  # type: ignore

SCRIPT_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPT_DIR / "registry.json"
DATASETS_DIR = SCRIPT_DIR / "datasets"


def load_registry() -> dict:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "fastrr-evals/1.0"})
    with urlopen(req) as resp:
        data = resp.read()
    dest.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download eval datasets to evals/datasets/",
        epilog="Run with --list to see available datasets.",
    )
    parser.add_argument(
        "datasets",
        nargs="*",
        help="Dataset names to download (e.g. locomo10, longmemeval_oracle)",
    )
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--all", action="store_true", help="Download all registered datasets")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    registry = load_registry()

    if args.list:
        for name, meta in registry.items():
            desc = meta.get("description", "")
            print(f"  {name}: {desc}")
        return 0

    to_download = list(registry.keys()) if args.all else args.datasets
    if not to_download:
        parser.print_help()
        print("\nNo datasets specified. Use --list to see options, or --all to download all.")
        return 1

    unknown = [d for d in to_download if d not in registry]
    if unknown:
        print(f"Unknown dataset(s): {unknown}", file=sys.stderr)
        print("Run with --list to see available datasets.", file=sys.stderr)
        return 1

    for name in to_download:
        meta = registry[name]
        url = meta["url"]
        filename = meta["filename"]
        dest = DATASETS_DIR / filename
        if not args.quiet:
            print(f"Downloading {name} -> {dest} ...")
        try:
            download(url, dest)
            if not args.quiet:
                size_mb = dest.stat().st_size / (1024 * 1024)
                print(f"  Done ({size_mb:.2f} MB)")
        except Exception as e:
            print(f"  Failed: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
