#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Generate the farm part of Nifegun's tileable crop farm for N sprinklers (10N + 2 crop tiles).

Pattern taken from a working 22-tile farm (N=2): farm arm rows at y=2 and y=6, sideways arms
at both ends of y=4, sprinklers at x=2+5k on y=4, tilled soil on y=3, y=5 and the two end
tiles of y=4, and a belt loop around the outside (left side up, top right, right side down,
bottom left). Torches fill the untilled middle-row tiles between sprinklers. The seed section is not included.

Usage:
    uv run tools/blueprints/farm_body.py <N> <out.json> <name>
    uv run tools/blueprints/farm_body.py --compare <captured 22-tile farm.json>
"""

import argparse
import sys
from pathlib import Path

from bplib import CONVEYOR_BELT, ROBOT_FARM_ARM, SPRINKLER, TORCH, Layout, Piece, Pos

SPRINKLER_SPACING = 5
MAX_SPRINKLERS = 8
BELT_UP, BELT_RIGHT, BELT_DOWN, BELT_LEFT = (Piece(CONVEYOR_BELT, variation=v) for v in range(4))
FARM_ARM = Piece(ROBOT_FARM_ARM)
SIDEWAYS_FARM_ARM = Piece(ROBOT_FARM_ARM, variation=1)


def farm_body(sprinklers: int) -> Layout:
    width = SPRINKLER_SPACING * sprinklers
    layout = Layout()
    for x in range(width):
        layout.put((x, 2), FARM_ARM)
        layout.put((x, 6), FARM_ARM)
        layout.put((x, 1), BELT_LEFT)
        layout.put((x, 7), BELT_RIGHT)
        layout.till((x, 3))
        layout.till((x, 5))
    layout.put((0, 4), SIDEWAYS_FARM_ARM)
    layout.put((width - 1, 4), SIDEWAYS_FARM_ARM)
    layout.till((1, 4))
    layout.till((width - 2, 4))
    for k in range(sprinklers):
        layout.put((2 + SPRINKLER_SPACING * k, 4), Piece(SPRINKLER))
    for k in range(sprinklers - 1):  # light: torches on every untilled middle-row tile between two sprinklers
        for x in range(3, SPRINKLER_SPACING + 2):
            layout.put((x + SPRINKLER_SPACING * k, 4), Piece(TORCH))
    for y in range(1, 7):
        layout.put((-1, y), BELT_UP)
    layout.put((-1, 7), BELT_RIGHT)
    layout.put((width, 7), BELT_DOWN)
    layout.put((width, 1), BELT_LEFT)
    for y in range(2, 7):
        layout.put((width, y), BELT_DOWN)
    return layout


def compare(captured_path: Path) -> None:
    """Check the 2-sprinkler body against a captured farm (whose x is shifted by +1)."""
    body_ids = {ROBOT_FARM_ARM, SPRINKLER, CONVEYOR_BELT}
    generated = farm_body(2)
    captured = Layout.load(captured_path)

    def objects(layout: Layout, shift: int) -> dict[Pos, list[tuple[int, int]]]:
        out: dict[Pos, list[tuple[int, int]]] = {}
        for (x, y), entities in layout.cells.items():
            found = sorted((e["ObjectID"], e["Variation"]) for e in entities if e["ObjectID"] in body_ids)
            if found and x + shift <= 2 * SPRINKLER_SPACING:
                out[(x + shift, y)] = found
        return out

    want, have = objects(generated, 0), objects(captured, -1)
    diff = {p: (want.get(p), have.get(p)) for p in want.keys() | have.keys() if want.get(p) != have.get(p)}
    soil_same = {(x - 1, y) for x, y in captured.tiles} == set(generated.tiles)
    print("object cells that differ (generated, captured):", diff or "none")
    print("soil identical:", soil_same)


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--compare", type=Path, metavar="CAPTURED_JSON", help="self-test against a captured farm")
    parser.add_argument("sprinklers", nargs="?", type=int, choices=range(1, MAX_SPRINKLERS + 1))
    parser.add_argument("out", nargs="?", type=Path)
    parser.add_argument("name", nargs="?")
    args = parser.parse_args()
    if args.compare:
        compare(args.compare)
        return
    if args.sprinklers is None or args.out is None or args.name is None:
        sys.exit("give N, the output file and the blueprint name, or --compare")
    n: int = args.sprinklers
    farm_body(n).write(
        args.out,
        args.name,
        f"Nifegun tileable crop farm body, {n} sprinklers, {10 * n + 2} crop tiles. "
        "No seed section: build it by hand from the video.",
    )


if __name__ == "__main__":
    main()
