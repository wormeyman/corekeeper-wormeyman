#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Generate two 20-chest crafting hubs (normal and double chests).

The smelting loop used to be generated here too. It now comes from a build captured in the game
(tools/blueprints/fix_smelt.py), so this script no longer writes it.

Crafting reach, from the game's code (Pug.Other InventoryUtility): a sphere of radius 10 around
the station, measured to each chest's box, keeping the 20 closest chests.

Usage:
    uv run tools/blueprints/build_smelt_craft.py <output folder>
"""

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

from bplib import (
    CHEST,
    GHORM_CHEST,
    TORCH,
    Layout,
    LayoutError,
    Piece,
    Pos,
)

CRAFTING_REACH = 10.0
CRAFTING_CHEST_LIMIT = 20
# Plan this far inside the reach: the chest collider sizes the game measures to are not checked.
REACH_MARGIN = 0.5


@dataclass(frozen=True)
class Station:
    object_id: int
    label: str
    width: int = 1


STATIONS = [  # non-seasonal crafting stations; widths from the wiki's data file
    Station(4003, "Basic Workbench"), Station(4043, "Copper Workbench"), Station(4019, "Tin Workbench"),
    Station(4010, "Iron Workbench"), Station(4016, "Scarlet Workbench"), Station(4027, "Octarine Workbench"),
    Station(4033, "Galaxite Workbench"), Station(4049, "Solarite Workbench"),
    Station(4011, "Copper Anvil"), Station(4020, "Tin Anvil"), Station(4014, "Iron Anvil"),
    Station(4021, "Scarlet Anvil"), Station(4024, "Octarine Anvil"), Station(4034, "Galaxite Anvil"),
    Station(4047, "Solarite Anvil"),
    Station(4005, "Electronics Table"), Station(4022, "Automation Table"), Station(4055, "Advanced Automation Table"),
    Station(4017, "Railway Forge"), Station(4008, "Alchemy Table"), Station(4026, "Distillery Table"),
    Station(4053, "Laboratory Table"), Station(4012, "Jewelry Workbench"),
    Station(4030, "Proficient Jewelry Workbench"),
    Station(4056, "Relucite Smithing Table"), Station(4060, "Metalcrafter's Table"), Station(4007, "Carpenter's Table"),
    Station(4018, "Painter's Table"), Station(4045, "Glass Workbench"), Station(4041, "Loom"),
    Station(4052, "Pouch Workbench"), Station(4035, "Key Casting Table"), Station(4028, "Fishing Workbench"),
    Station(4048, "Livestock Workbench"), Station(4051, "Hydra Altar"), Station(4025, "Salvage and Repair Station"),
    Station(4046, "Upgrade Station", 2), Station(4031, "Boat Workbench", 2),
    Station(4036, "Go-Kart Workbench", 2), Station(4042, "Music Workbench", 2),
]  # fmt: skip


def ring(corner_low: Pos, corner_high: Pos) -> list[tuple[Pos, str]]:
    """Tiles of a rectangle's border, clockwise from the bottom-left, each with its side."""
    (x0, y0), (x1, y1) = corner_low, corner_high
    tiles = [((x, y0), "bottom") for x in range(x0, x1 + 1)]
    tiles += [((x1, y), "right") for y in range(y0 + 1, y1 + 1)]
    tiles += [((x, y1), "top") for x in range(x1 - 1, x0 - 1, -1)]
    tiles += [((x0, y), "left") for y in range(y1 - 1, y0, -1)]
    return tiles


def distance_to_box(point: Pos, box: Pos, width: int = 1) -> float:
    """Distance from a tile centre to the nearest edge of a box `width` tiles wide, as the game's sphere test does."""
    dx = max(box[0] - 0.5 - point[0], point[0] - (box[0] + width - 0.5), 0)
    dy = max(abs(point[1] - box[1]) - 0.5, 0)
    return math.hypot(dx, dy)


def crafting_hub(chest: Piece) -> tuple[Layout, float]:
    """20 chests in two 2-wide columns with an aisle between, a walkway ring, then two rings of stations.

    Every chest touches the aisle or the walkway; players can't open a chest from two tiles away.
    The doorway at the bottom lines up with the aisle.
    """
    layout = Layout()
    w = chest.size[0]
    aisle_x, right = 2 * w, 4 * w  # the aisle's column; the chest block's right edge
    chests = [(x, y) for x in (0, w, aisle_x + 1, aisle_x + 1 + w) for y in range(5)]
    for c in chests:
        layout.put(c, chest)

    def in_reach(p: Pos) -> bool:
        return all(distance_to_box(p, c, w) <= CRAFTING_REACH - REACH_MARGIN for c in chests)

    inner_corners = {(-2, -2), (right + 2, -2), (-2, 6), (right + 2, 6)}  # only touch the walkway diagonally
    inner = [p for p, _ in ring((-2, -2), (right + 2, 6)) if p not in inner_corners]
    outer = [p for p, _ in ring((-3, -3), (right + 3, 7))]
    doorway = {(aisle_x, -2), (aisle_x, -3)}
    free = [p for p in inner + outer if p not in doorway and in_reach(p)]

    placed: list[Pos] = []
    top_y = 7
    for station in (s for s in STATIONS if s.width > 1):  # along the outer ring's top
        x = next((x for x in range(-3, right + 3) if all((x + dx, top_y) in free for dx in range(station.width))), None)
        if x is None:
            raise LayoutError(f"no room in reach on the top row for {station.label}")
        tiles = [(x + dx, top_y) for dx in range(station.width)]
        layout.put((x, top_y), Piece(station.object_id, size=(station.width, 1)))
        placed += tiles
        free = [p for p in free if p not in tiles]
    narrow = [s for s in STATIONS if s.width == 1]
    if len(free) < len(narrow):
        raise LayoutError(f"{len(narrow)} stations but only {len(free)} ring slots in reach")
    for station, pos in zip(narrow, free, strict=False):
        layout.put(pos, Piece(station.object_id))
        placed.append(pos)
    worst = max(distance_to_box(p, c, w) for p in placed for c in chests)
    if worst > CRAFTING_REACH:
        raise LayoutError(f"a station is {worst:.2f} tiles from a chest; the game's limit is {CRAFTING_REACH}")
    if len(chests) > CRAFTING_CHEST_LIMIT:
        raise LayoutError(f"{len(chests)} chests, but stations only use the {CRAFTING_CHEST_LIMIT} closest")
    for corner in inner_corners:  # light: the inner ring's corners stay empty, since no station there is reachable
        layout.put(corner, Piece(TORCH))
    layout.check_access()
    return layout, worst


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("folder", type=Path)
    folder: Path = parser.parse_args().folder

    common = (
        "Stations in two rings within 10 tiles of every chest; doorway at the bottom middle. "
        "Keep other chests more than 10 tiles from every station."
    )
    for name, chest, note in (
        ("Crafting hub - 20 chests", Piece(CHEST), "20 chests in two columns with an aisle between."),
        (
            "Crafting hub - 20 double chests",
            Piece(GHORM_CHEST, size=(2, 1)),
            "20 double (boss) chests, 36 slots each. Pasting needs 20 Ghorm Chests; without them, put any "
            "boss chests on the empty 2-wide spots.",
        ),
    ):
        hub, worst = crafting_hub(chest)
        print(f"{name}: {len(STATIONS)} stations, farthest station-to-chest distance {worst:.2f}")
        hub.write(folder / f"{name}.json", name, f"{note} {common}")


if __name__ == "__main__":
    main()
