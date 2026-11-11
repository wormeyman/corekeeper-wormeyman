#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Add the seed extractor corner to the fixed farm blueprint, write it under a new name.

Coordinates are the fixed file's (original farm x + 1). From Nifegun's tutorial screenshot:
seed extractor top-left of the splitter section, robot arm to its right feeding it.
Usage: add_corner.py <fixed.json> <dest.json> <name>
"""
import json, sys

SEED_EXTRACTOR, ROBOT_ARM = 6657, 6652
src, dest, name = sys.argv[1:4]
bp = json.load(open(src, encoding="utf-8"))
cells = {tuple(i["Position"]): i for i in bp["EntityInfos"]}

def add(x, y, oid, variation=0, direction=(0, 0)):
    if (x, y) in cells:
        sys.exit(f"cell {(x, y)} not empty")
    cells[(x, y)] = {"Entities": [{"ObjectID": oid, "X": 1, "Y": 1, "Variation": variation,
                                   "Direction": list(direction), "Color": 0}], "Position": [x, y]}

# Existing arm at (12,6), variation 2, feeds the tile above it: (12,7) is the extractor.
assert any(e["ObjectID"] == ROBOT_ARM and e["Variation"] == 2 for e in cells[(12, 6)]["Entities"])
add(12, 7, SEED_EXTRACTOR, direction=(-1, 0))   # output = position + direction -> loop corner (11,7)
add(13, 7, ROBOT_ARM, variation=1)               # takes from (14,7) (splitter (14,6) output), drops into (12,7)
assert (14, 7) not in cells, "arm source tile must stay empty"

bp["Name"] = name
bp["Description"] = ("Nifegun 22-slot crop farm. Loop closed, soil and seed extractor corner added by script; "
                     "set robot arm filters after pasting.")
bp["EntityInfos"] = sorted(cells.values(), key=lambda i: (i["Position"][1], i["Position"][0]))
with open(dest, "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(bp, indent=2, ensure_ascii=False))
print(f"wrote {dest}")
