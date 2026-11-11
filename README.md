# Core Keeper notes and blueprints

Notes, blueprints and small tools for Core Keeper: mods worth having, how automation works, and ready-made builds for the [BuildingBlueprint](https://steamcommunity.com/sharedfiles/filedetails/?id=3753254765) mod.

The save fix for running Core Keeper through CrossOver on a Mac lives in its own repo: [core-keeper-crossover-save-fix](https://github.com/wormeyman/core-keeper-crossover-save-fix).

This project is not made by or connected to Pugstorm or Fireshine Games.

## What's here

- **[docs/mods.md](docs/mods.md):** other people's mods (blueprints, tile grid, food), how BuildingBlueprint works, automation parts for crop farms, a tileable crop farm design, grid sizes and startup logos.
- **[docs/crafting-and-smelting.md](docs/crafting-and-smelting.md):** how crafting stations use nearby chests, a crafting room layout that follows those rules, and how robot arms work with smelters.
- **[blueprints/](blueprints):** ready-made BuildingBlueprint files.
- **[tools/](tools):** scripts that read, check and generate blueprints, and read the game's code.

## Blueprints

None of these has been pasted in the game yet. Paste each one away from your real builds first.

| File | Size | What it is | After pasting |
|---|---|---|---|
| `Farm 22 - fixed.json` | 17 x 8 | Nifegun's 2-sprinkler crop farm, 22 crop tiles | Set two filters: the item collector (the purple "vacuum" right of the loop) to the normal crop, and the bottom robot arm that reaches onto the loop to the golden crop. Leave the other arms unfiltered. Drop 22 seeds on the loop and about 12 crops in the seed extractor. |
| `Farm 82 - body only.json` | 42 x 7 | The 8-sprinkler version's farm part, 82 crop tiles | Build the seed section by hand ([video](https://youtu.be/ULqGPiiX-yM), 7:51 to 10:45), then capture the whole farm. |
| `Dirt pad - 10 x 10.json`, `Dirt pad - 50 x 30.json` | 10 x 10, 50 x 30 | Plain dirt ground, for spots with no floor (pits, water) | Try the small one first: filling a pit or water this way is untested. |
| `Smelting loop - 10 ores.json` | 18 x 9 | Ore chest in, bar chest out, one smelter per ore | Filters are not saved. Set the 10 loading arms (between the belt and the smelters), left to right: copper, tin, iron, gold, scarlet, octarine, galaxite, solarite, pandorium, relucite ore. |
| `Crafting hub - 20 chests.json` | 10 x 11 | 20 chests in two columns with an aisle, 40 stations around them | Keep other chests more than 10 tiles from the stations. |
| `Crafting hub - 20 double chests.json` | 13 x 11 | The same with 20 double (boss) chests, twice the storage | Needs 20 Ghorm Chests to paste fully; otherwise place any boss chests in the 2-wide gaps. |

The farm design is from [Simple and Efficient Automatic Crop Farming](https://youtu.be/ULqGPiiX-yM) by Nifegun. Notes on it are in [docs/mods.md](docs/mods.md#a-tileable-crop-farm-design).

**Torches are built in.** Each blueprint has torches on tiles nothing else uses (the farms' untilled middle row, the hubs' inner corners), so you can see it working. Take them out after pasting if you light the area another way.

**Pasting uses your items.** Each piece takes one matching item from your inventory, and missing pieces are skipped without a warning. Tilled soil needs a hoe, which isn't used up. Run `tools/blueprint_report.py` on a file to see its map and shopping list.

### Adding a blueprint to the game

Either way works:

- **Import:** open the JSON file, copy all of it, then in the game open the blueprint panel (**B**) and press Import. It reads the clipboard.
- **Copy the file:** with the game closed, put it in the mod's blueprint folder, inside the game's per-player data folder. On Linux that is `~/.config/unity3d/Pugstorm/Core Keeper/Steam/<STEAM_ID>/mods/BuildingBlueprint/Default/`.

## Tools

They are Python scripts that run with [uv](https://docs.astral.sh/uv/), which installs their packages by itself. They only read game files. None of them runs game code. On Linux they find the game in the default Steam folder. Elsewhere, pass the game's `CoreKeeper_Data/Managed` folder.

- **`tools/blueprint_report.py <blueprint.json>`** draws a blueprint as a grid and lists the items one paste needs.
- **`tools/blueprints/farm_body.py <N> <out.json> <name>`** makes the farm part of Nifegun's crop farm for 1 to 8 sprinklers (10N + 2 crop tiles). `--compare` checks it against a captured farm.
- **`tools/blueprints/build_smelt_craft.py <folder>`** writes the smelting loop and both crafting hubs, and checks them: no overlaps, every arm points from its source to its target, every station reaches every chest, and every chest and station touches floor the player can walk to.
- **`tools/blueprints/dirt_pad.py <width> <height> <out.json> <name>`** makes a rectangle of dirt ground tiles of any size.
- **`tools/blueprints/fix_farm.py <captured.json> <out.json> <name>`** turned a captured 22-tile farm into `Farm 22 - fixed`: it closes the belt loop and adds the soil and the seed extractor corner.
- **`tools/blueprints/bplib.py`** is the shared code the generators use: facing rules, object IDs, overlap checks and the blueprint file format.
- **`tools/gamecode/`** reads the game's DLLs and the mod's asset bundle: `object_ids.py` (object and enum names), `il_decode.py` (a method's code, with names and numbers), `list_types.py`, `list_methods.py` and `mod_tile_filter.py` (BuildingBlueprint's tile filter list).

## Checks

The scripts are checked with [ruff](https://docs.astral.sh/ruff/) and [Pyrefly](https://pyrefly.org/) in strict mode, on every push (`.github/workflows/check.yml`). To run them yourself:

```sh
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pyrefly check
```

## Facing, for anyone writing blueprints

Facing is stored as the variation number: 0 up, 1 right, 2 down, 3 left (`DirectionBasedOnVariationCD` in the game's code). A belt moves items in its facing direction. A robot arm takes from the tile one step in its facing direction and drops one step the other way. A seed extractor drops seeds in the direction of its separate `Direction` field.

## License

MIT. See [LICENSE](LICENSE).
