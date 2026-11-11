#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["UnityPy"]
# ///
"""List TileType values of TileTargetDataBlock assets in a mod asset bundle (read only)."""
import sys
import UnityPy

env = UnityPy.load(sys.argv[1])
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        tree = obj.read_typetree()
    except Exception:
        raw = obj.get_raw_data()
        continue
    if "TileType" in tree:
        print(tree.get("m_Name"), tree["TileType"])
