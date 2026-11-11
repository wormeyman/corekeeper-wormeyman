"""Shared helpers for writing BuildingBlueprint files.

Facing rules, checked against a working farm and the game's code:
- variation 0 up, 1 right, 2 down, 3 left (DirectionBasedOnVariationCD.GetDirectionFromVariation)
- a belt moves items toward direction(variation)
- a robot arm takes from position + direction(variation) and drops at position - direction(variation)
- a seed extractor drops its output at position + its Direction field (the game's DirectionCD)
Multi-tile objects are stored at their bottom-left tile. That assumes the object's
prefabCornerOffset is 0, which has not been checked in the game.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

type Pos = tuple[int, int]

DIRECTION: dict[int, Pos] = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}

# Object IDs from the game's ObjectID enum (Pug.Base.dll)
CHEST = 100
GHORM_CHEST = 172  # a 2x1 boss chest with 36 slots
ELECTRICAL_WIRE = 6501
UNDERGROUND_GENERATOR = 6518
CONVEYOR_BELT = 6651
ROBOT_ARM = 6652
SPRINKLER = 6653
SEED_EXTRACTOR = 6657
ROBOT_FARM_ARM = 6658
FURNACE = 4004
SMELTER_KILN = 4015
FURY_FORGE = 4032
# TileType enum
DUG_UP_GROUND = 49
TILESET_DIRT = 0

# Layers, as seen in a working farm: wires and the lowered generator sit under anything
# (belts, robot arms, torches); a belt can't share a tile with a solid object.
UNDER_OBJECTS = frozenset({ELECTRICAL_WIRE, UNDERGROUND_GENERATOR})
FLOOR_OBJECTS = frozenset({CONVEYOR_BELT})


class EntityJson(TypedDict):
    ObjectID: int
    X: int
    Y: int
    Variation: int
    Direction: list[int]
    Color: int


class EntityInfoJson(TypedDict):
    Entities: list[EntityJson]
    Position: list[int]


class TileJson(TypedDict):
    tileset: int
    tileType: int


class TileInfoJson(TypedDict):
    Position: list[int]
    Tiles: list[TileJson]


class BlueprintJson(TypedDict):
    Name: str
    Description: str
    EntityInfos: list[EntityInfoJson]
    TileInfos: list[TileInfoJson]
    Size: list[int]


class LayoutError(Exception):
    """The layout breaks a rule: an overlap, or an arm whose source and target don't line up."""


def variation_for(direction: Pos) -> int:
    """The variation whose facing is `direction`."""
    for variation, d in DIRECTION.items():
        if d == direction:
            return variation
    raise LayoutError(f"{direction} is not one of the four facings")


@dataclass(frozen=True)
class Piece:
    object_id: int
    size: Pos = (1, 1)
    variation: int = 0
    direction: Pos = (0, 0)
    color: int = 0  # paint (PaintableColor); 0 is unpainted

    def to_json(self) -> EntityJson:
        return {
            "ObjectID": self.object_id,
            "X": self.size[0],
            "Y": self.size[1],
            "Variation": self.variation,
            "Direction": list(self.direction),
            "Color": self.color,
        }


class Layout:
    """Objects and tiles on a grid, with overlap checks, written out as a blueprint."""

    def __init__(self) -> None:
        self.cells: dict[Pos, list[EntityJson]] = {}
        self.tiles: dict[Pos, list[TileJson]] = {}
        self.solid: set[Pos] = set()
        self.floor: set[Pos] = set()
        self.under: set[Pos] = set()

    def put(self, pos: Pos, piece: Piece) -> None:
        footprint = [(pos[0] + dx, pos[1] + dy) for dx in range(piece.size[0]) for dy in range(piece.size[1])]
        if piece.object_id in UNDER_OBJECTS:
            self.under.update(footprint)
        else:
            floor = piece.object_id in FLOOR_OBJECTS
            for t in footprint:
                if t in self.solid or (t in self.floor and not floor):
                    raise LayoutError(f"{t} is taken; cannot place object {piece.object_id}")
            (self.floor if floor else self.solid).update(footprint)
        self.cells.setdefault(pos, []).append(piece.to_json())

    def arm(self, pos: Pos, source: Pos, target: Pos) -> None:
        """Place a robot arm that takes from `source` and drops at `target`."""
        d = (source[0] - pos[0], source[1] - pos[1])
        if (pos[0] - d[0], pos[1] - d[1]) != target:
            raise LayoutError(f"arm at {pos}: source {source} and target {target} are not on opposite sides")
        self.put(pos, Piece(ROBOT_ARM, variation=variation_for(d)))

    def till(self, pos: Pos, tileset: int = TILESET_DIRT) -> None:
        if pos in self.solid:
            raise LayoutError(f"{pos} has an object on it; cannot till")
        self.tiles.setdefault(pos, []).append({"tileset": tileset, "tileType": DUG_UP_GROUND})

    def objects_at(self, pos: Pos) -> set[int]:
        return {e["ObjectID"] for e in self.cells.get(pos, [])}

    def check_access(self) -> None:
        """Raise unless every solid object has a side touching floor a player can walk to from outside.

        Players in the game could not open chests two tiles from the floor, so this asks for a
        shared side, not a diagonal.
        """
        xs = [p[0] for p in self.solid]
        ys = [p[1] for p in self.solid]
        lo, hi = (min(xs) - 1, min(ys) - 1), (max(xs) + 1, max(ys) + 1)
        walkable: set[Pos] = set()
        todo = [lo]
        while todo:
            p = todo.pop()
            inside = lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1]
            if p in walkable or p in self.solid or not inside:
                continue
            walkable.add(p)
            todo += [(p[0] + d[0], p[1] + d[1]) for d in DIRECTION.values()]
        stuck = [
            (pos, e["ObjectID"])
            for pos, entities in self.cells.items()
            for e in entities
            if e["ObjectID"] not in UNDER_OBJECTS | FLOOR_OBJECTS
            and not any(
                (pos[0] + dx + d[0], pos[1] + dy + d[1]) in walkable
                for dx in range(e["X"])
                for dy in range(e["Y"])
                for d in DIRECTION.values()
            )
        ]
        if stuck:
            raise LayoutError(f"no walkable side for (position, object): {stuck}")

    @classmethod
    def load(cls, path: Path) -> Layout:
        data: BlueprintJson = json.loads(path.read_text(encoding="utf-8-sig"))
        layout = cls()
        for info in data["EntityInfos"]:
            x, y = info["Position"]
            for e in info["Entities"]:
                direction = (e["Direction"][0], e["Direction"][1])
                piece = Piece(e["ObjectID"], (e["X"], e["Y"]), e["Variation"], direction, e["Color"])
                layout.put((x, y), piece)
        for tile_info in data["TileInfos"]:
            x, y = tile_info["Position"]
            layout.tiles[(x, y)] = list(tile_info["Tiles"])
        return layout

    def to_json(self, name: str, description: str) -> BlueprintJson:
        """Shift everything so the lowest x and y are 0, as the mod's own Save() does."""
        used = self.solid | self.floor | self.under | {p for p, ts in self.tiles.items() if ts}
        mx, my = min(p[0] for p in used), min(p[1] for p in used)

        def order(p: Pos) -> Pos:
            return (p[1], p[0])

        return {
            "Name": name,
            "Description": description,
            "EntityInfos": [
                {"Entities": self.cells[p], "Position": [p[0] - mx, p[1] - my]} for p in sorted(self.cells, key=order)
            ],
            "TileInfos": [
                {"Position": [p[0] - mx, p[1] - my], "Tiles": self.tiles[p]}
                for p in sorted(self.tiles, key=order)
                if self.tiles[p]
            ],
            "Size": [max(p[0] for p in used) - mx, max(p[1] for p in used) - my],
        }

    def write(self, path: Path, name: str, description: str) -> BlueprintJson:
        data = self.to_json(name, description)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        width, height = data["Size"][0] + 1, data["Size"][1] + 1
        print(f"wrote {path} ({width} x {height} tiles)")
        return data
