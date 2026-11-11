#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Write a fixed copy of a captured 22-slot farm blueprint (Nifegun design): close the belt loop and add tilled soil.

Belt flow in the saved farm runs down the right side (x=10, variation 2) and left along the
bottom (y=1, variation 3), so the loop continues up the left side (variation 0) and right
along the top (variation 1), then down into (10,6). Variation: 0 up, 1 right, 2 down, 3 left.
Usage: fix_farm.py <source.json> <dest.json> <name> [tileset]
"""
import json, sys

CONVEYOR, DUG_UP_GROUND = 6651, 49
src, dest, name = sys.argv[1:4]
tileset = int(sys.argv[4]) if len(sys.argv) > 4 else 0  # 0 = Dirt
bp = json.load(open(src, encoding="utf-8"))
cells = {tuple(i["Position"]): i for i in bp["EntityInfos"]}

def add_belt(x, y, variation):
    if (x, y) in cells:
        sys.exit(f"cell {(x, y)} is not empty; refusing to overwrite")
    cells[(x, y)] = {"Entities": [{"ObjectID": CONVEYOR, "X": 1, "Y": 1, "Variation": variation,
                                   "Direction": [0, 0], "Color": 0}], "Position": [x, y]}

for y in range(1, 7):
    add_belt(-1, y, 0)          # left side, flowing up
add_belt(-1, 7, 1)              # top-left corner, turning right
for x in range(0, 10):
    add_belt(x, 7, 1)           # top side, flowing right
add_belt(10, 7, 2)              # top-right corner, turning down into (10,6)

# 22 crop tiles: rows y=3 and y=5 (x 0-9), plus (1,4) and (8,4) beside the sideways arms.
soil = [(x, y) for y in (3, 5) for x in range(10)] + [(1, 4), (8, 4)]
for p in soil:
    if p in cells:
        sys.exit(f"crop tile {p} has an object on it; layout is not what we expect")
tiles = [{"Position": [x, y], "Tiles": [{"tileset": tileset, "tileType": DUG_UP_GROUND}]} for x, y in soil]

# Re-base so the lowest x and y are 0, as the mod's own Save() does.
allpos = list(cells) + soil
mx, my = min(p[0] for p in allpos), min(p[1] for p in allpos)
for info in cells.values():
    info["Position"] = [info["Position"][0] - mx, info["Position"][1] - my]
for t in tiles:
    t["Position"] = [t["Position"][0] - mx, t["Position"][1] - my]
out = {
    "Name": name,
    "Description": "Nifegun 22-slot crop farm. Belt loop closed and soil added by script. Seed extractor corner still missing.",
    "EntityInfos": sorted(cells.values(), key=lambda i: (i["Position"][1], i["Position"][0])),
    "TileInfos": tiles,
    "Size": [max(p[0] for p in allpos) - mx, max(p[1] for p in allpos) - my],
}
with open(dest, "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(out, indent=2, ensure_ascii=False))
print(f"wrote {dest}: {sum(len(i['Entities']) for i in cells.values())} objects, {len(tiles)} soil tiles, size {out['Size']}")
