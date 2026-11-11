#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["UnityPy"]
# ///
"""List the tile types in BuildingBlueprint's tile filter, read from the mod's asset bundle. Read only.

Usage:
    uv run tools/gamecode/mod_tile_filter.py <BuildingBlueprint_Linux.assetbundle>
"""

import argparse
import sys
from pathlib import Path

import UnityPy


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle: Path = args.bundle
    env = UnityPy.load(str(bundle))
    unreadable = 0
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:  # noqa: BLE001 - UnityPy raises many types for scripts it has no layout for
            unreadable += 1
        else:
            if isinstance(tree, dict) and "TileType" in tree:
                print(tree.get("m_Name"), tree["TileType"])
    if unreadable:
        print(f"({unreadable} other script objects had no readable layout and were skipped)", file=sys.stderr)


if __name__ == "__main__":
    main()
