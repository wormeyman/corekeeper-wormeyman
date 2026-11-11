# CLAUDE.md

Guidance for Claude Code in this repo.

## What this is

Core Keeper notes, BuildingBlueprint blueprints and small Python tools. The CrossOver save fix is a separate repo (`wormeyman/core-keeper-crossover-save-fix`); its .NET tools (`CompileCheck`, `InspectMethods`, `WineFileCheck`) stay there.

## Public repo

Do not commit Steam IDs, save data, world or character names, absolute home paths, or the owner's name outside `LICENSE`. Blueprints captured from a real game go through a check for those before they are added.

## Conventions

- Python, as uv scripts with a PEP 723 block (`requires-python = ">=3.14"`). Run with `uv run tools/...`. The one exception is `tools/modcheck/`, which also holds the C# project and .editorconfig it runs.
- Changes to other people's C# mods go as small, single-purpose commits and PRs. Each commit passes `tools/modcheck/modcheck.py`: no new compiler errors, no new analyzer warnings, clean formatting in the files it touches. Prove a new gate can fail with a deliberately bad commit before trusting it.
- Checks: `uv run ruff format --check .`, `uv run ruff check .`, `uv run pyrefly check` (strict). CI runs the same. All must pass; no blanket ignores.
- The generators in `tools/blueprints/` share `bplib.py` (they import it as a neighbour). After changing one, regenerate its blueprint and diff it against `blueprints/` with keys and positions sorted.
- Tools only read game files (`dnfile` for DLLs, `UnityPy` for asset bundles). Never run game code.
- Every fact in `docs/` says where it came from: code (name the type or method), wiki, a video, or a player's game. Say what is untested.
- Prose stays at a 12th grade reading level or below. Use hyphens, not em or en dashes.

## Game facts the tools rely on

- Facing: variation 0 up, 1 right, 2 down, 3 left. Belts flow in their facing direction. Robot arms take from position + direction and drop at position - direction. A seed extractor's output uses its `Direction` field (the game's `DirectionCD`).
- BuildingBlueprint stores a multi-tile object at its position, with the footprint starting at position + `prefabCornerOffset`. The generators assume that offset is 0 (bottom-left), which is not yet checked in the game.
- Pasting takes one matching item per piece from the player's inventory and skips missing ones silently. Filters, chest contents and settings are not saved.
- Crafting stations use the 20 closest chests within a radius of 10 around the station.
- A player can only open a chest that shares a side with floor they can stand on (seen in the game: chests inside a solid 5 x 4 block could not be opened). `Layout.check_access` enforces this.

## Testing in the game

Only the user can run the game. Before writing to the game's blueprint folder, check that the game is closed with `ps -eo comm`, because `pgrep -f` matches its own command line.
