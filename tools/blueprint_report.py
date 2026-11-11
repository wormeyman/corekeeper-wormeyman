#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["dnfile"]
# ///
"""Show what a BuildingBlueprint mod blueprint holds: a map and the items one paste needs.

Blueprints store objects and tiles as numbers. This script reads the names from the
game's own Pug.Base.dll (read only; no game code runs). Multi-tile objects are drawn from
their stored position up and to the right.

Usage:
    uv run tools/blueprint_report.py <blueprint.json> [--managed <CoreKeeper_Data/Managed>]
"""

import argparse
import json
import string
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import dnfile

DEFAULT_MANAGED = Path.home() / ".local/share/Steam/steamapps/common/Core Keeper/CoreKeeper_Data/Managed"
MAX_CONSTANT_BYTES = 8
OBJECT_SYMBOLS = string.ascii_uppercase + string.digits + "#$%&*+=@"
TILE_SYMBOLS = string.ascii_lowercase
MIN_CELL_WIDTH = 2

# Tiles that paste without using up an item of their own (from the mod's BuildingPlaceServer).
TILE_NOTES = {
    "dugUpGround": "needs any hoe in your inventory; the hoe is not used up",
    "water": "uses a filled bucket",
    "roofHole": "uses a Roofing Tool",
    "ground": "uses a dirt (or matching) wall block",
}

type Pos = tuple[int, int]


def read_enum(dll: Path, type_name: str) -> dict[int, str]:
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
        if str(t.TypeName) == type_name:
            return {constants[f.row_index]: str(f.row.Name) for f in t.FieldList if f.row_index in constants and f.row}
    sys.exit(f"{type_name} not found in {dll}")


@dataclass
class Report:
    cells: dict[Pos, str] = field(default_factory=dict)
    legend: dict[str, str] = field(default_factory=dict)
    objects: Counter[str] = field(default_factory=Counter)
    tiles: Counter[tuple[str, int]] = field(default_factory=Counter)

    def mark(self, pos: Pos, symbol: str) -> None:
        if symbol not in self.cells.get(pos, ""):
            self.cells[pos] = self.cells.get(pos, "") + symbol


def collect(blueprint: dict[str, Any], object_names: dict[int, str], tile_names: dict[int, str]) -> Report:
    report = Report()
    object_symbols, tile_symbols = iter(OBJECT_SYMBOLS), iter(TILE_SYMBOLS)
    symbol_for: dict[str, str] = {}
    for info in blueprint.get("EntityInfos", []):
        x, y = info["Position"]
        for e in info["Entities"]:
            oid: int = e["ObjectID"]
            name = object_names.get(oid, f"unknown object {oid}")
            if name not in symbol_for:
                symbol_for[name] = next(object_symbols, "?")
                report.legend[symbol_for[name]] = name
            for dx in range(e.get("X", 1)):
                for dy in range(e.get("Y", 1)):
                    report.mark((x + dx, y + dy), symbol_for[name])
            report.objects[name] += 1  # variations (often which way it faces) share one item
    for info in blueprint.get("TileInfos", []):
        x, y = info["Position"]
        for t in info["Tiles"]:
            tile_id: int = t["tileType"]
            name = tile_names.get(tile_id, f"unknown tile {tile_id}")
            key = f"tile:{name}"
            if key not in symbol_for:
                symbol_for[key] = next(tile_symbols, "?")
                report.legend[symbol_for[key]] = f"{name} (tile)"
            report.mark((x, y), symbol_for[key])
            report.tiles[(name, t.get("tileset", 0))] += 1
    return report


def print_map(report: Report) -> None:
    xs = [p[0] for p in report.cells]
    ys = [p[1] for p in report.cells]
    print(f"Footprint: {max(xs) - min(xs) + 1} x {max(ys) - min(ys) + 1} tiles\n")
    width = max(MIN_CELL_WIDTH, *(len(v) for v in report.cells.values()))
    columns = range(min(xs), max(xs) + 1)
    for y in range(max(ys), min(ys) - 1, -1):
        row = " ".join(report.cells.get((x, y), ".").ljust(width) for x in columns)
        print(f"{y:>3} {row}")
    print("    " + " ".join(str(x).ljust(width) for x in columns))
    print("\nLegend:")
    for symbol, name in report.legend.items():
        print(f"  {symbol}  {name}")


def print_lists(report: Report) -> None:
    print("\nObjects to carry (one used per object):")
    for name, n in sorted(report.objects.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {n:>4}  {name}")
    if report.tiles:
        print("\nTiles (most use one matching block or floor item each):")
        for (name, tileset), n in sorted(report.tiles.items(), key=lambda kv: (-kv[1], kv[0])):
            note = TILE_NOTES.get(name, "")
            print(f"  {n:>4}  {name} (tileset {tileset})" + (f" - {note}" if note else ""))
    print(
        "\nMissing items are skipped without a warning. Planted crops cannot be pasted"
        " outside creative God Mode, because the mod looks for the plant object, not the seed."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("blueprint", type=Path)
    parser.add_argument(
        "--managed", type=Path, default=DEFAULT_MANAGED, help="the game's CoreKeeper_Data/Managed folder"
    )
    args = parser.parse_args()
    managed: Path = args.managed
    blueprint_path: Path = args.blueprint

    base = managed / "Pug.Base.dll"
    blueprint: dict[str, Any] = json.loads(blueprint_path.read_text(encoding="utf-8-sig"))
    report = collect(blueprint, read_enum(base, "ObjectID"), read_enum(base, "TileType"))
    print(f"Blueprint: {blueprint.get('Name')}  {blueprint.get('Description') or ''}".rstrip())
    if not report.cells:
        print("Empty blueprint.")
        return
    print_map(report)
    print_lists(report)


if __name__ == "__main__":
    main()
