# Crafting areas and smelting

Notes from November 2026, for setting up a crafting room and an automatic smelter. Each fact says where it came from. "Code" means the game's own DLLs, read with `tools/gamecode/` (read only, no game code runs). "Wiki" means the [Core Keeper wiki](https://corekeeper.atma.gg/en/Crafting) and its data file. Nothing here has been tested on purpose in the game yet.

## How stations use nearby chests

All from the code (`CraftingHandler.GetNearbyChests` and `InventoryUtility` in `Pug.Other.dll`, constants in `Pug.Base.dll`):

- A station looks for chests in a **circle of radius 10 around the station itself**. Where you stand doesn't matter.
- The distance is measured to the **nearest edge** of each chest's collision box, not its center. That is why a two-tile chest counts if either half is in range.
- The station keeps only the **20 closest** chests (`craftingChestMaxAmount = 20`). Some players report 22. This build's code says 20.
- Each station picks its own 20. With more than 20 chests in range, two stations can see different chests, and a station can seem to "stop pulling items".
- Quick stack to nearby chests uses the same rule: 10 tiles, 20 chests.

### Layout that follows these rules

Put the chests in the **middle** and the stations around them. The popular [Efficient Crafting Area](https://steamcommunity.com/sharedfiles/filedetails/?id=3431575585) guide does the opposite, with chests around the walls. Then stations near one wall can't reach the chests on the far wall.

**Every chest needs a side touching the floor.** In a test in the game, the player could not open chests in the middle of a solid 5 x 4 block. So the chests stand in two columns, each two chests wide, with an aisle between them. Each chest touches the aisle or the walkway around the block. The generator checks this: every chest and station must share a side with floor the player can walk to.

Keep all other chests more than 10 tiles from every station.

There are two versions of the hub. Both have 40 stations in two rings around a walkway, with a doorway at the bottom that lines up with the aisle. The inner ring's corners stay empty, because they only touch the walkway at a corner.

- **`blueprints/Crafting hub - 20 chests.json`** uses normal chests (18 slots each, 360 in all). The farthest station is 9.2 tiles from the farthest chest.
- **`blueprints/Crafting hub - 20 double chests.json`** uses double chests (36 slots each, 720 in all). Double chests are the 2 x 1 chests bosses drop (wiki). The blueprint uses Ghorm Chests, and pasting takes that exact item. Without 20 of them, paste anyway and put any boss chests on the empty 2-wide spots. The farthest station is 9.3 tiles from the farthest chest.

Both plan for 9.5 tiles, not the full 10. The game measures to each chest's collider, and the collider sizes have not been checked.

### Crafting stations in this build

The game's object list (code) has these normal crafting stations, besides seasonal ones:

- **Workbenches (8 tiers):** Basic, Copper, Tin, Iron, Scarlet, Octarine, Galaxite, Solarite.
- **Anvils (7 tiers):** Copper, Tin, Iron, Scarlet, Octarine, Galaxite, Solarite.
- **Other tables:** Alchemy, Distillery, Laboratory, Carpenter's, Painter's, Electronics, Automation, Advanced Automation, Railway Forge, Jewelry, Proficient Jewelry, Relucite Smithing, Metalcrafter's, Glass Workbench, Loom, Pouch Workbench, Key Casting, Fishing Workbench, Livestock Workbench, Hydra Altar, Salvage and Repair Station, Upgrade Station, Boat Workbench, Go-Kart Workbench, Music Workbench.
- **New, not in the wiki data yet:** Big Industrial Table and Small Industrial Table. Their size is unknown, so the hub blueprint leaves them out. Both versions have spare ring spots for them.

Sizes come from the wiki's data file (`Module:Data.json`). Most stations are 1 x 1. Upgrade, Boat, Go-Kart and Music are 2 x 1.

## Smelting

Which machine smelts which ore (wiki data):

| Machine | Size | Bars |
|---|---|---|
| Furnace | 1 x 1 | Copper, Tin, Iron |
| Smelter Kiln | 1 x 1 | Gold, Scarlet, Octarine |
| Fury Forge | 2 x 2 | Galaxite, Solarite, Pandorium, Relucite |
| Glass Smelter | 1 x 1 | Glass, from sand blocks |

None of them needs power. Robot arms do.

### How robot arms treat smelters

From the code:

- An arm that **takes from a smelter only takes from its output slot** (`InventoryUtility.CanPickup` checks `CraftingCD.outputSlotIndex`). It never pulls ore back out.
- An arm that **picks up from a belt only checks its own filter** (`MoverMoveAndPickupJob`). It doesn't check whether the machine it feeds can use the item. So an arm feeding a smelter needs a filter for that smelter's ore. Without one, it will grab any item on the belt.
- An arm takes from the tile one step in its facing direction, and drops one step the other way. This matches a working farm.

### The smelting loop blueprint

`blueprints/Smelting loop - 10 ores.json` (18 x 9 tiles) uses those rules:

1. Ore goes into the bottom-left chest. An arm puts it on a belt loop.
2. Ore circles the loop. Next to each smelter, a loading arm filtered to one ore pulls that ore in.
3. Unloading arms take finished bars and put them on an output belt.
4. A last arm puts the bars into the top-left chest.

It has one smelter per ore: 3 Furnaces, 3 Smelter Kilns and 4 Fury Forges. A lowered generator and 14 wires power all 22 arms.

**After pasting, set the 10 loading-arm filters by hand.** BuildingBlueprint doesn't save filters. The blueprint's description lists which column gets which ore.

**Not known yet:**

- What a loading arm does when its smelter's input is full: wait, or drop the ore.
- Whether a 2 x 2 forge is anchored at its bottom-left tile, as the blueprint assumes.
- Whether belts jam when the loop gets very full.

Test with a small mixed batch first.
