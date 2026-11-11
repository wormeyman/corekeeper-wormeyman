#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Complete a captured 22-tile crop farm (Nifegun design) that missed parts of the build.

The capture that `Farm 22 - fixed.json` came from left out the loop's left and top sides, the
tilled soil and the seed extractor corner. This adds them:
- belts continuing the saved flow (right side down, bottom left), so up the left side and
  right along the top, then down into the right side
- tilled soil on the 22 crop tiles, and torches on the four tiles between the two sprinklers
- a seed extractor at the top-left of the splitter section, dropping seeds west onto the loop,
  and a robot arm to its right feeding it from the splitter below (from the tutorial's frames)

Coordinates below are the captured file's (farm arm columns 0-9, loop's right side at x=10).

Usage:
    uv run tools/blueprints/fix_farm.py <captured.json> <out.json> <name> [--tileset N]
"""

import argparse
from pathlib import Path

from bplib import CONVEYOR_BELT, ROBOT_ARM, SEED_EXTRACTOR, TILESET_DIRT, TORCH, Layout, LayoutError, Piece

BELT_UP, BELT_RIGHT, BELT_DOWN = (Piece(CONVEYOR_BELT, variation=v) for v in (0, 1, 2))
LOOP_RIGHT_X, LOOP_TOP_Y = 10, 7
SOIL = [(x, y) for y in (3, 5) for x in range(10)] + [(1, 4), (8, 4)]
EXTRACTOR_ARM_BELOW = (11, 6)  # already in the capture; drops into the tile above it
MIDDLE_TORCHES = [(x, 4) for x in range(3, 7)]  # every untilled tile between the two sprinklers


def complete(layout: Layout, tileset: int) -> None:
    for y in range(1, LOOP_TOP_Y):
        layout.put((-1, y), BELT_UP)
    layout.put((-1, LOOP_TOP_Y), BELT_RIGHT)
    for x in range(LOOP_RIGHT_X):
        layout.put((x, LOOP_TOP_Y), BELT_RIGHT)
    layout.put((LOOP_RIGHT_X, LOOP_TOP_Y), BELT_DOWN)
    for pos in SOIL:
        layout.till(pos, tileset)
    for pos in MIDDLE_TORCHES:
        layout.put(pos, Piece(TORCH))
    if ROBOT_ARM not in layout.objects_at(EXTRACTOR_ARM_BELOW):
        raise LayoutError(f"expected the captured robot arm at {EXTRACTOR_ARM_BELOW}; is this the right farm?")
    extractor = (EXTRACTOR_ARM_BELOW[0], LOOP_TOP_Y)
    layout.put(extractor, Piece(SEED_EXTRACTOR, direction=(-1, 0)))  # output = position + direction
    feeder = (extractor[0] + 1, LOOP_TOP_Y)
    layout.arm(feeder, source=(feeder[0] + 1, LOOP_TOP_Y), target=extractor)


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("captured", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("name")
    parser.add_argument("--tileset", type=int, default=TILESET_DIRT, help="soil look; 0 is Dirt")
    args = parser.parse_args()
    layout = Layout.load(args.captured)
    complete(layout, args.tileset)
    layout.write(
        args.out,
        args.name,
        "Nifegun 22-slot crop farm. Loop closed, soil and seed extractor corner added by script; "
        "set robot arm filters after pasting.",
    )


if __name__ == "__main__":
    main()
