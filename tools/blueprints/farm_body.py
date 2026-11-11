#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Generate the farm body of Nifegun's tileable crop farm for N sprinklers (10N+2 crop tiles).

Pattern taken from a working 22-tile farm (N=2): farm arm rows at y=2 and y=6, sideways
arms at the ends of y=4, sprinklers at x=2+5k on y=4, soil on y=3, y=5 and the two end tiles
of y=4, and a belt loop around the outside (left side up, top right, right side down, bottom
left). Variation: 0 up, 1 right, 2 down, 3 left. The seed section is not included.
Usage: farm_body.py <N> <dest.json> <name>     (N=2 with --compare <fixed.json> self-tests)
"""
import json, sys

FARM_ARM, SPRINKLER, BELT, DUG = 6658, 6653, 6651, 49

def body(n):
    w = 5 * n
    ents, soil = {}, []
    def put(x, y, oid, v=0): ents.setdefault((x, y), []).append((oid, v))
    for x in range(w):
        put(x, 2, FARM_ARM); put(x, 6, FARM_ARM)
        put(x, 1, BELT, 3); put(x, 7, BELT, 1)
        soil += [(x, 3), (x, 5)]
    put(0, 4, FARM_ARM, 1); put(w - 1, 4, FARM_ARM, 1)
    soil += [(1, 4), (w - 2, 4)]
    for k in range(n): put(2 + 5 * k, 4, SPRINKLER)
    for y in range(1, 7): put(-1, y, BELT, 0)
    put(-1, 7, BELT, 1); put(w, 7, BELT, 2); put(w, 1, BELT, 3)
    for y in range(2, 7): put(w, y, BELT, 2)
    return ents, soil

if sys.argv[1] == "--compare":
    fixed = json.load(open(sys.argv[2]))
    ents, soil = body(2)
    want = {(x + 1, y): sorted(v) for (x, y), v in ents.items()}  # fixed file is shifted +1 in x
    have = {}
    for i in fixed["EntityInfos"]:
        p = tuple(i["Position"])
        if p[0] <= 11:   # body columns only (x -1..10 original)
            have[p] = sorted((e["ObjectID"], e["Variation"]) for e in i["Entities"] if e["ObjectID"] in (FARM_ARM, SPRINKLER, BELT))
    have = {k: v for k, v in have.items() if v}
    diff = {p: (want.get(p), have.get(p)) for p in set(want) | set(have) if want.get(p) != have.get(p)}
    fsoil = {tuple(t["Position"]) for t in fixed["TileInfos"]}
    print("entity cells differing:", diff or "none")
    print("soil identical:", fsoil == {(x + 1, y) for x, y in soil})
    sys.exit()

n, dest, name = int(sys.argv[1]), sys.argv[2], sys.argv[3]
ents, soil = body(n)
cells = set(ents) | set(soil)
mx, my = min(p[0] for p in cells), min(p[1] for p in cells)
out = {
    "Name": name,
    "Description": f"Nifegun tileable crop farm body, {n} sprinklers, {10*n+2} crop tiles. No seed section: build it by hand from the video.",
    "EntityInfos": [{"Entities": [{"ObjectID": o, "X": 1, "Y": 1, "Variation": v, "Direction": [0, 0], "Color": 0} for o, v in vs],
                     "Position": [x - mx, y - my]} for (x, y), vs in sorted(ents.items(), key=lambda kv: (kv[0][1], kv[0][0]))],
    "TileInfos": [{"Position": [x - mx, y - my], "Tiles": [{"tileset": 0, "tileType": DUG}]} for x, y in soil],
    "Size": [max(p[0] for p in cells) - mx, max(p[1] for p in cells) - my],
}
open(dest, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2))
print(f"wrote {dest}")
