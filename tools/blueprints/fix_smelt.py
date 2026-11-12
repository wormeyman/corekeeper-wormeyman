#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Turn a captured 10-ore smelting loop (lamp design) into `Smelting loop - 10 ores`.

The loop was built and fixed in the game on 2026-11-11, then captured. Lamps carry the power and
light it, and the bar belt ends at a lamp so bars stop where the bar arm can reach them. The
capture needs two fixes:
- the ore input arm beside the bottom-left chest faced the belt, so it would move ore from the
  belt into the chest; it is turned to take from the chest and drop onto the loop's first belt
- three loading arms came out without their filters (galaxite, solarite, relucite); they are set

Coordinates below are the captured file's (input chest at (0, 1), loading arms on y = 2).

Usage:
    uv run tools/blueprints/fix_smelt.py <captured.json> <out.json> <name>
"""

import argparse
from pathlib import Path

from bplib import (
    CHEST,
    CONVEYOR_BELT,
    GALAXITE_ORE,
    RELUCITE_ORE,
    ROBOT_ARM,
    SOLARITE_ORE,
    WHITELIST,
    EntityJson,
    Layout,
    LayoutError,
    Pos,
    variation_for,
)

INPUT_CHEST, INPUT_ARM, LOOP_START = (0, 1), (1, 1), (2, 1)
MISSING_FILTERS: dict[Pos, int] = {(9, 2): GALAXITE_ORE, (11, 2): SOLARITE_ORE, (15, 2): RELUCITE_ORE}
ORE_ORDER = "copper, tin, iron, gold, scarlet, octarine, galaxite, solarite, pandorium, relucite"


def arm_at(layout: Layout, pos: Pos) -> EntityJson:
    arms = [e for e in layout.cells.get(pos, []) if e["ObjectID"] == ROBOT_ARM]
    if len(arms) != 1:
        raise LayoutError(f"expected one robot arm at {pos}; is this the right capture?")
    return arms[0]


def fix(layout: Layout) -> None:
    if CHEST not in layout.objects_at(INPUT_CHEST) or CONVEYOR_BELT not in layout.objects_at(LOOP_START):
        raise LayoutError(f"expected the ore chest at {INPUT_CHEST} and a belt at {LOOP_START}")
    # an arm takes from the tile it faces and drops on the tile behind it
    arm_at(layout, INPUT_ARM)["Variation"] = variation_for(
        (INPUT_CHEST[0] - INPUT_ARM[0], INPUT_CHEST[1] - INPUT_ARM[1])
    )
    for pos, ore in MISSING_FILTERS.items():
        arm = arm_at(layout, pos)
        if arm.get("FilterType"):
            raise LayoutError(f"arm at {pos} already has a filter; is this the right capture?")
        arm["FilterType"] = WHITELIST
        arm["FilterObject"] = ore
        arm["FilterVariation"] = 0
    # No layout.check_access(): the smelters sit between the loading and unloading arms with no walkable
    # side, and nobody needs to open them; the arms fill and empty them. Both chests are on the open west edge.


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("captured", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("name")
    args = parser.parse_args()
    layout = Layout.load(args.captured)
    fix(layout)
    layout.write(
        args.out,
        args.name,
        "Ores into the bottom-left chest, bars out of the top-left chest. Lamps carry the power and light. "
        "The loading-arm filters are in this file, but the published mod skips them; if they come out unset, "
        f"set the loading arms (the row between the belt and the smelters), left to right: {ORE_ORDER} ore. "
        "Leave the other arms unfiltered.",
    )


if __name__ == "__main__":
    main()
