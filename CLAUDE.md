# CLAUDE.md

Guidance for Claude Code in this repo.

## What this is

Core Keeper notes, BuildingBlueprint blueprints and small Python tools. The CrossOver save fix is a separate repo (`wormeyman/core-keeper-crossover-save-fix`); its .NET tools (`CompileCheck`, `InspectMethods`, `WineFileCheck`) stay there.

## Public repo

Do not commit Steam IDs, save data, world or character names, absolute home paths, or the owner's name outside `LICENSE`. Blueprints captured from a real game go through a check for those before they are added.

## Conventions

- Python only, as uv scripts with a PEP 723 block (`requires-python = ">=3.14"`). Run with `uv run tools/...`.
- Tools only read game files (`dnfile` for DLLs, `UnityPy` for asset bundles). Never run game code.
- Every fact in `docs/` says where it came from: code (name the type or method), wiki, a video, or a player's game. Say what is untested.
- Prose stays at a 12th grade reading level or below. Use hyphens, not em or en dashes.

## Game facts the tools rely on

- Facing: variation 0 up, 1 right, 2 down, 3 left. Belts flow in their facing direction. Robot arms take from position + direction and drop at position - direction. A seed extractor's output uses its `Direction` field (the game's `DirectionCD`).
- BuildingBlueprint stores a multi-tile object at its position, with the footprint starting at position + `prefabCornerOffset`. The generators assume that offset is 0 (bottom-left), which is not yet checked in the game.
- Pasting takes one matching item per piece from the player's inventory and skips missing ones silently. Filters, chest contents and settings are not saved.
- Crafting stations use the 20 closest chests within a radius of 10 around the station.

## Testing in the game

Only the user can run the game. Before writing to the game's blueprint folder, check that the game is closed with `ps -eo comm`, because `pgrep -f` matches its own command line.
