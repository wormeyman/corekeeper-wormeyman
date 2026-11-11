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

import argparse
import sys
from pathlib import Path

import dnfile

MAX_CONSTANT_BYTES = 8  # enum backing types are at most 64-bit


def enum_values(dll: Path, enum_name: str) -> dict[int, str]:
    """Return {value: name} for an enum type in a .NET DLL."""
    net = dnfile.dnPE(str(dll)).net
    md = net.mdtables if net else None
    if md is None or md.TypeDef is None or md.Constant is None:
        sys.exit(f"{dll} is not a .NET assembly")
    constants: dict[int, int] = {}
    for c in md.Constant:
        parent = c.Parent
        # dnfile's hints say bytes, but at runtime this is a heap item holding the bytes in .value
        raw = bytes(getattr(c.Value, "value", c.Value))
        if parent.table and parent.table.name == "Field" and len(raw) <= MAX_CONSTANT_BYTES:
            constants[parent.row_index] = int.from_bytes(raw, "little", signed=True)
    for t in md.TypeDef:
        if str(t.TypeName) == enum_name:
            return {constants[f.row_index]: str(f.row.Name) for f in t.FieldList if f.row_index in constants and f.row}
    sys.exit(f"no enum {enum_name} in {dll}")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("dll", type=Path)
    parser.add_argument("numbers", nargs="*", type=int, help="only print these values")
    parser.add_argument("--enum", default="ObjectID", help="enum type name (default ObjectID)")
    args = parser.parse_args()
    wanted: set[int] = set(args.numbers)
    for value, name in sorted(enum_values(args.dll, args.enum).items()):
        if not wanted or value in wanted:
            print(value, name)


if __name__ == "__main__":
    main()
