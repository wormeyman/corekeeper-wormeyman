#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Generate a 10-ore smelting loop and two 20-chest crafting hubs (normal and double chests).

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
    CONVEYOR_BELT,
    ELECTRICAL_WIRE,
    FURNACE,
    FURY_FORGE,
    GHORM_CHEST,
    SMELTER_KILN,
    TORCH,
    UNDERGROUND_GENERATOR,
    Layout,
    LayoutError,
    Piece,
    Pos,
)

BELT_UP, BELT_RIGHT, BELT_DOWN, BELT_LEFT = (Piece(CONVEYOR_BELT, variation=v) for v in range(4))
WIRE = Piece(ELECTRICAL_WIRE)
CRAFTING_REACH = 10.0
CRAFTING_CHEST_LIMIT = 20
# Plan this far inside the reach: the chest collider sizes the game measures to are not checked.
REACH_MARGIN = 0.5


@dataclass(frozen=True)
class Smelter:
    object_id: int
    size: int
    ore: str


SMELTERS = [
    Smelter(FURNACE, 1, "copper"), Smelter(FURNACE, 1, "tin"), Smelter(FURNACE, 1, "iron"),
    Smelter(SMELTER_KILN, 1, "gold"), Smelter(SMELTER_KILN, 1, "scarlet"), Smelter(SMELTER_KILN, 1, "octarine"),
    Smelter(FURY_FORGE, 2, "galaxite"), Smelter(FURY_FORGE, 2, "solarite"),
    Smelter(FURY_FORGE, 2, "pandorium"), Smelter(FURY_FORGE, 2, "relucite"),
]  # fmt: skip


def smelting_loop() -> tuple[Layout, list[tuple[int, Smelter]]]:
    """Ore chest -> belt loop -> filtered loading arms -> smelters -> unloading arms -> bar chest."""
    layout = Layout()
    columns: list[tuple[int, Smelter]] = []
    x = 0
    for smelter in SMELTERS:
        columns.append((x, smelter))
        x += smelter.size
    east = x  # first column after the smelters
    # belt loop: y=1 flows east, y=0 flows west, joined at x=-1 and x=east
    for i in range(-1, east):
        layout.put((i, 1), BELT_RIGHT)
    layout.put((east, 1), BELT_DOWN)
    for i in range(east + 1):
        layout.put((i, 0), BELT_LEFT)
    layout.put((-1, 0), BELT_UP)
    # the ore chest feeds the loop's corner
    layout.put((-1, -2), Piece(CHEST))
    layout.arm((-1, -1), source=(-1, -2), target=(-1, 0))
    last_small = max(cx for cx, s in columns if s.size == 1)
    for cx, smelter in columns:
        s = smelter.size
        layout.put((cx, 3), Piece(smelter.object_id, size=(s, s)))
        layout.arm((cx, 2), source=(cx, 1), target=(cx, 3))  # loading arm: filter to smelter.ore by hand
        top = 3 + s - 1
        layout.arm((cx, top + 1), source=(cx, top), target=(cx, top + 2))  # unloading arm: takes bars only
        for extra in range(1, s):  # carry power across a 2-wide forge
            layout.put((cx + extra, 2), WIRE)
            layout.put((cx + extra, top + 1), WIRE)
    # output belt: y=6 over the forges flowing west, a step down at last_small, then y=5 west to x=-1
    for i in range(last_small + 1, east):
        layout.put((i, 6), BELT_LEFT)
    layout.put((last_small, 6), BELT_DOWN)
    for i in range(-1, last_small + 1):
        layout.put((i, 5), BELT_LEFT)
    layout.put((-3, 5), Piece(CHEST))  # bar chest
    layout.arm((-2, 5), source=(-1, 5), target=(-3, 5))
    # power: a lowered generator beside the loading row, wire up the west column and across the step
    layout.put((-1, 2), Piece(UNDERGROUND_GENERATOR))
    for y in (0, 1, 3, 4, 5):
        layout.put((-1, y), WIRE)
    layout.put((last_small, 5), WIRE)
    # light: torches on free tiles below the loop, beside the bar chest, past the east end and over the furnaces
    for pos in ((2, -1), (8, -1), (east, -1), (-3, 1), (east, 5), (2, 6)):
        layout.put(pos, Piece(TORCH))
    return layout, columns


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

    loop, columns = smelting_loop()
    filters = ", ".join(f"x{cx} {s.ore}" for cx, s in columns)
    loop.write(
        folder / "Smelting loop - 10 ores.json",
        "Smelting loop - 10 ores",
        f"Ores into the bottom-left chest, bars out of the top-left chest. Set each loading arm's filter: {filters}",
    )
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
