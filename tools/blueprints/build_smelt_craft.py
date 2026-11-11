#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Generate two BuildingBlueprint files: a 10-ore smelting loop and a 20-chest crafting hub.

Facing rules (checked against a working farm and the game code):
- variation 0 up, 1 right, 2 down, 3 left (DirectionBasedOnVariationCD)
- belt: items flow toward direction(variation)
- robot arm: takes from position + direction(variation), drops at position - direction(variation)
Multi-tile objects are stored at their bottom-left tile (assumes prefabCornerOffset 0).
Crafting reach (Pug.Other InventoryUtility): sphere radius 10 from the station to each chest's box,
20 closest chests only.
Usage: build_smelt_craft.py <blueprint folder>
"""
import json, math, sys
from pathlib import Path

DIR = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}
def var_for(d): return {v: k for k, v in DIR.items()}[d]

CHEST, BELT, ARM, WIRE, GEN = 100, 6651, 6652, 6501, 6518
FURNACE, KILN, FORGE = 4004, 4015, 4032

class BP:
    def __init__(self): self.cells = {}; self.occupied = {}
    def put(self, x, y, oid, v=0, size=(1, 1), floor=False):
        # floor objects (belts, wires, lowered generator) may share a tile with each other
        for dx in range(size[0]):
            for dy in range(size[1]):
                t = (x + dx, y + dy)
                kind = "floor" if floor else "solid"
                prev = self.occupied.get(t)
                if prev == "solid" or (prev and kind == "solid"):
                    sys.exit(f"overlap at {t} placing {oid}")
                self.occupied[t] = prev or kind if floor else "solid"
        self.cells.setdefault((x, y), []).append({"ObjectID": oid, "X": size[0], "Y": size[1], "Variation": v,
                                                  "Direction": [0, 0], "Color": 0})
    def arm(self, x, y, src, dst):
        d = (src[0] - x, src[1] - y)
        assert (x - d[0], y - d[1]) == dst, f"arm at {(x, y)}: source and target are not opposite"
        self.put(x, y, ARM, var_for(d))
    def write(self, path, name, desc):
        xs = [p[0] for p in self.occupied]; ys = [p[1] for p in self.occupied]
        mx, my = min(xs), min(ys)
        out = {"Name": name, "Description": desc,
               "EntityInfos": [{"Entities": ents, "Position": [x - mx, y - my]}
                               for (x, y), ents in sorted(self.cells.items(), key=lambda kv: (kv[0][1], kv[0][0]))],
               "TileInfos": [], "Size": [max(xs) - mx, max(ys) - my]}
        Path(path).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"wrote {path}  footprint {max(xs)-mx+1} x {max(ys)-my+1}")

def smelter(folder):
    b = BP()
    machines = [(FURNACE, 1, "copper"), (FURNACE, 1, "tin"), (FURNACE, 1, "iron"),
                (KILN, 1, "gold"), (KILN, 1, "scarlet"), (KILN, 1, "octarine"),
                (FORGE, 2, "galaxite"), (FORGE, 2, "solarite"), (FORGE, 2, "pandorium"), (FORGE, 2, "relucite")]
    x, cols = 0, []
    for oid, s, ore in machines:
        cols.append((x, oid, s, ore)); x += s
    east = x  # first column after the machines
    # belt loop: y=1 flows east, y=0 flows west, joined at x=-1 and x=east
    for i in range(-1, east): b.put(i, 1, BELT, 1, floor=True)
    b.put(east, 1, BELT, 2, floor=True)
    for i in range(0, east + 1): b.put(i, 0, BELT, 3, floor=True)
    b.put(-1, 0, BELT, 0, floor=True)
    # input chest feeds the loop corner
    b.put(-1, -2, CHEST); b.arm(-1, -1, src=(-1, -2), dst=(-1, 0))
    last_small = max(c[0] for c in cols if c[2] == 1)
    for cx, oid, s, ore in cols:
        b.put(cx, 3, oid, size=(s, s))
        b.arm(cx, 2, src=(cx, 1), dst=(cx, 3))                  # loading arm: filter to `ore` by hand
        top = 3 + s - 1
        b.arm(cx, top + 1, src=(cx, top), dst=(cx, top + 2))   # unloading arm: takes bars only
        for extra in range(1, s):                              # bridge power across 2-wide forges
            b.put(cx + extra, 2, WIRE, floor=True); b.put(cx + extra, top + 1, WIRE, floor=True)
    # output belt: y=6 over the forges flowing west, step down at last_small, y=5 west to x=-1
    for i in range(last_small + 1, east): b.put(i, 6, BELT, 3, floor=True)
    b.put(last_small, 6, BELT, 2, floor=True)
    for i in range(-1, last_small + 1): b.put(i, 5, BELT, 3, floor=True)
    b.put(-3, 5, CHEST); b.arm(-2, 5, src=(-1, 5), dst=(-3, 5))  # bar chest
    # power: generator beside the loading row, wire up the west column and across the step
    b.put(-1, 2, GEN, floor=True)
    for y in (-1 + 1, 1, 3, 4, 5): b.put(-1, y, WIRE, floor=True)  # (-1,0),(-1,1) under belts
    b.put(last_small, 5, WIRE, floor=True)
    b.write(Path(folder) / "Smelting loop - 10 ores.json", "Smelting loop - 10 ores",
            "Ores into the bottom-left chest, bars out of the top-left chest. Set each loading arm's filter: "
            + ", ".join(f"x{c[0]} {c[3]}" for c in cols))
    return b, cols

STATIONS = [  # (ObjectID, size, label) - non-seasonal crafting stations, sizes from the wiki data
    (4003, 1, "Basic Workbench"), (4043, 1, "Copper Workbench"), (4019, 1, "Tin Workbench"), (4010, 1, "Iron Workbench"),
    (4016, 1, "Scarlet Workbench"), (4027, 1, "Octarine Workbench"), (4033, 1, "Galaxite Workbench"), (4049, 1, "Solarite Workbench"),
    (4011, 1, "Copper Anvil"), (4020, 1, "Tin Anvil"), (4014, 1, "Iron Anvil"), (4021, 1, "Scarlet Anvil"),
    (4024, 1, "Octarine Anvil"), (4034, 1, "Galaxite Anvil"), (4047, 1, "Solarite Anvil"),
    (4005, 1, "Electronics Table"), (4022, 1, "Automation Table"), (4055, 1, "Advanced Automation Table"), (4017, 1, "Railway Forge"),
    (4008, 1, "Alchemy Table"), (4026, 1, "Distillery Table"), (4053, 1, "Laboratory Table"),
    (4012, 1, "Jewelry Workbench"), (4030, 1, "Proficient Jewelry Workbench"), (4056, 1, "Relucite Smithing Table"), (4060, 1, "Metalcrafter's Table"),
    (4007, 1, "Carpenter's Table"), (4018, 1, "Painter's Table"), (4045, 1, "Glass Workbench"), (4041, 1, "Loom"),
    (4052, 1, "Pouch Workbench"), (4035, 1, "Key Casting Table"), (4028, 1, "Fishing Workbench"), (4048, 1, "Livestock Workbench"),
    (4051, 1, "Hydra Altar"), (4025, 1, "Salvage and Repair Station"),
    (4046, 2, "Upgrade Station"), (4031, 2, "Boat Workbench"), (4036, 2, "Go-Kart Workbench"), (4042, 2, "Music Workbench"),
]

def ring(x0, y0, x1, y1):
    """Tiles of a rectangle's border, clockwise from the bottom-left, as (x, y, side)."""
    out = [(x, y0, "bottom") for x in range(x0, x1 + 1)]
    out += [(x1, y, "right") for y in range(y0 + 1, y1 + 1)]
    out += [(x, y1, "top") for x in range(x1 - 1, x0 - 1, -1)]
    out += [(x0, y, "left") for y in range(y1 - 1, y0, -1)]
    return out

def crafting(folder):
    b = BP()
    chests = [(x, y) for x in range(5) for y in range(4)]
    for c in chests: b.put(*c, CHEST)
    door = 2  # doorway column through both station rings on the bottom side
    inner = [t for t in ring(-2, -2, 6, 5) if not (t[2] == "bottom" and t[0] == door)]
    outer = [t for t in ring(-3, -3, 7, 6) if not (t[2] == "bottom" and t[0] == door)]
    wide = [s for s in STATIONS if s[1] == 2]; small = [s for s in STATIONS if s[1] == 1]
    # 2-wide stations go on the outer ring's top side, left to right, with a gap between them
    top = sorted([t for t in outer if t[2] == "top"], key=lambda t: t[0])
    used, placed = set(), []
    xs = [t[0] for t in top]
    pos = xs[0]
    for oid, s, label in wide:
        b.put(pos, 6, oid, size=(2, 1)); used |= {(pos, 6), (pos + 1, 6)}; placed.append((label, [(pos, 6), (pos + 1, 6)])); pos += 3
    slots = [(x, y) for x, y, _ in inner + outer if (x, y) not in used]
    if len(slots) < len(small): sys.exit("not enough ring slots")
    for (oid, s, label), (x, y) in zip(small, slots):
        b.put(x, y, oid); placed.append((label, [(x, y)]))
    # reach check: every tile of every station within 10 of every chest box
    def d(px, py, cx, cy): return math.hypot(max(abs(px - cx) - .5, 0), max(abs(py - cy) - .5, 0))
    worst = max(d(px, py, cx, cy) for _, ts in placed for px, py in ts for cx, cy in chests)
    print(f"crafting hub: {len(placed)} stations, {len(slots) - len(small)} spare ring slots, worst station-to-chest distance {worst:.2f} (limit 10)")
    assert worst <= 10
    b.write(Path(folder) / "Crafting hub - 20 chests.json", "Crafting hub - 20 chests",
            "20 chests in the middle, stations in two rings within 10 tiles of every chest; doorway at the bottom middle. "
            "Keep other chests more than 10 tiles from every station.")
    return placed

if __name__ == "__main__":
    folder = sys.argv[1]
    smelter(folder)
    crafting(folder)
