#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# ///
"""Generate a rectangle of plain dirt ground tiles, to fill gaps where there is no floor.

Pasting a ground tile uses one dirt block from your inventory (none in God Mode). Whether a
pasted ground tile replaces water or a pit has not been tested in the game; try a small pad first.

Usage:
    uv run tools/blueprints/dirt_pad.py <width> <height> <out.json> <name> [--tileset N]
"""

import argparse
from pathlib import Path

from bplib import GROUND, TILESET_DIRT, Layout


def dirt_pad(width: int, height: int, tileset: int) -> Layout:
    layout = Layout()
    for x in range(width):
        for y in range(height):
            layout.tile((x, y), GROUND, tileset)
    return layout


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("width", type=int)
    parser.add_argument("height", type=int)
    parser.add_argument("out", type=Path)
    parser.add_argument("name")
    parser.add_argument("--tileset", type=int, default=TILESET_DIRT, help="ground look; 0 is Dirt")
    args = parser.parse_args()
    width: int = args.width
    height: int = args.height
    if width < 1 or height < 1:
        parser.error("width and height must be at least 1")
    dirt_pad(width, height, args.tileset).write(
        args.out,
        args.name,
        f"{width} x {height} dirt ground, to fill gaps with no floor. Uses one dirt block per tile outside God Mode.",
    )


if __name__ == "__main__":
    main()
