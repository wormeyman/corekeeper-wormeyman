#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["dnfile"]
# ///
"""Print an enum's values from a game DLL (default: ObjectID), optionally only some numbers. Read only.

Usage:
    uv run tools/gamecode/object_ids.py <Pug.Base.dll> [number ...]
    uv run tools/gamecode/object_ids.py <Pug.Base.dll> --enum TileType [number ...]
"""
import sys

import dnfile

args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
dll, rest = args[0], args[1:]
enum = "ObjectID"
if rest[:1] == ["--enum"]:
    enum, rest = rest[1], rest[2:]
wanted = {int(a) for a in rest}
md = dnfile.dnPE(dll).net.mdtables
consts = {}
for c in md.Constant:
    p = c.Parent
    if p.table and p.table.name == "Field" and len(c.Value.value) <= 8:
        consts[p.row_index] = int.from_bytes(c.Value.value, "little", signed=True)
for t in md.TypeDef:
    if str(t.TypeName) != enum:
        continue
    for f in t.FieldList:
        if f.row_index in consts and (not wanted or consts[f.row_index] in wanted):
            print(consts[f.row_index], f.row.Name)
