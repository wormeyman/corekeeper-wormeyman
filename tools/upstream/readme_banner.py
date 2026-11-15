#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pillow>=13,<14"]
# ///
"""Build readme-banner.png for ReishyouSose/CoreKeeperMods (PR #7).

A title strip over a 4 x 2 grid of the 8 mods' own Steam Workshop preview images.
The previews and the Pixelify Sans font (SIL Open Font License) are downloaded into
the cache folder on first run. The Chinese subtitle needs a Noto Sans CJK collection.

    uv run tools/upstream/readme_banner.py <cache-dir> <out.png>
"""

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Workshop file IDs, in README table order. Coreria's folder in the repo is TerraZenith.
MODS = {
    "CoreEnhance": "3721031561",
    "CoreFighter": "3721040464",
    "AllSkills": "3721047666",
    "GeneralConfigMenu": "3721094795",
    "PointShop": "3721095168",
    "TrophyKeeper": "3721099336",
    "BuildingBlueprint": "3753254765",
    "Coreria": "3832200101",
}
# Previews with no mod name drawn on them get a name tag
UNTITLED = {"AllSkills"}

STEAM_API = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/pixelifysans/PixelifySans%5Bwght%5D.ttf"
CJK_DEFAULT = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"

WIDTH = 1920
COLS, ROWS = 4, 2
GAP = 12
TILE_W = (WIDTH - GAP * (COLS + 1)) // COLS
TILE_H = TILE_W * 9 // 16
HEADER_H = 190
HEIGHT = HEADER_H + ROWS * TILE_H + ROWS * GAP  # gap between rows and below the last one

BG = (16, 14, 24)
TITLE = (255, 214, 92)  # warm gold, close to the previews' title text
SUB = (200, 196, 220)
GREEN = (92, 226, 140)
BLACK = (0, 0, 0)


def fetch(url: str, data: bytes | None = None) -> bytes:
    if not url.startswith("https://"):
        raise SystemExit(f"refusing non-https URL: {url}")
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as r:  # noqa: S310 - https only
        return r.read()


def download(cache: Path) -> None:
    """Fetch the font and any missing preview images into the cache folder."""
    cache.mkdir(parents=True, exist_ok=True)
    font = cache / "PixelifySans.ttf"
    if not font.exists():
        font.write_bytes(fetch(FONT_URL))
    missing = {name: fid for name, fid in MODS.items() if not (cache / f"{name}.png").exists()}
    if not missing:
        return
    form = {"itemcount": str(len(missing))} | {f"publishedfileids[{i}]": fid for i, fid in enumerate(missing.values())}
    reply = json.loads(fetch(STEAM_API, urllib.parse.urlencode(form).encode()))
    by_id = {d["publishedfileid"]: d for d in reply["response"]["publishedfiledetails"]}
    for name, fid in missing.items():
        (cache / f"{name}.png").write_bytes(fetch(by_id[fid]["preview_url"]))


def cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale to fill w x h and crop the middle, like CSS object-fit: cover."""
    scale = max(w / img.width, h / img.height)
    resized = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    return resized.crop((left, top, left + w, top + h))


def contain(img: Image.Image, w: int, h: int) -> Image.Image:
    """Fit the whole image in w x h, over a blurred, darkened fill of itself."""
    back = cover(img, w, h).filter(ImageFilter.GaussianBlur(18))
    back = Image.blend(back, Image.new("RGB", back.size, BG), 0.55)
    scale = min(w / img.width, h / img.height)
    fg = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    back.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    return back


def rounded_mask(w: int, h: int, r: int) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return mask


def pixel_font(path: Path, size: int, weight: str) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size)
    font.set_variation_by_name(weight)
    return font


def cjk_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Pick the Simplified Chinese face out of a Noto CJK collection."""
    for index in range(10):
        font = ImageFont.truetype(path, size, index=index)
        if "SC" in (font.getname()[0] or ""):
            return font
    raise SystemExit(f"no Simplified Chinese (SC) face in {path}")


def build(cache: Path, cjk: str) -> Image.Image:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)
    previews = {name: Image.open(cache / f"{name}.png").convert("RGB") for name in MODS}

    # A blurred, darkened copy of the previews behind the header gives it the game's colors.
    strip = Image.new("RGB", (WIDTH, HEADER_H))
    part = WIDTH // len(MODS)
    for i, img in enumerate(previews.values()):
        strip.paste(cover(img, part + 1, HEADER_H), (i * part, 0))
    strip = Image.blend(strip.filter(ImageFilter.GaussianBlur(28)), Image.new("RGB", strip.size, BG), 0.72)
    canvas.paste(strip, (0, 0))

    font_path = cache / "PixelifySans.ttf"
    draw = ImageDraw.Draw(canvas)
    x = GAP + 18
    title = "ReishyouSose's Core Keeper Mods"
    title_font = pixel_font(font_path, 84, "Bold")
    # Hard pixel shadow, like the previews' outlined pixel titles
    draw.text((x + 5, 31), title, font=title_font, fill=BLACK)
    draw.text((x, 26), title, font=title_font, fill=TITLE)
    draw.text((x + 4, 124), "8 mods on the Steam Workshop", font=pixel_font(font_path, 36, "Medium"), fill=SUB)

    zh = "地心护核者模组合集"
    zh_font = cjk_font(cjk, 34)
    draw.text((WIDTH - GAP - 18 - draw.textlength(zh, font=zh_font), 124), zh, font=zh_font, fill=GREEN)

    mask = rounded_mask(TILE_W, TILE_H, 10)
    tag_font = pixel_font(font_path, 40, "Bold")
    for i, (name, img) in enumerate(previews.items()):
        tx = GAP + (i % COLS) * (TILE_W + GAP)
        ty = HEADER_H + (i // COLS) * (TILE_H + GAP)
        canvas.paste(contain(img, TILE_W, TILE_H), (tx, ty), mask)
        if name in UNTITLED:
            tw = draw.textlength(name, font=tag_font)
            box = (tx + (TILE_W - tw) / 2 - 18, ty + TILE_H - 74, tx + (TILE_W + tw) / 2 + 18, ty + TILE_H - 18)
            draw.rounded_rectangle(box, 8, fill=BG, outline=TITLE, width=3)
            draw.text((box[0] + 18, box[1] + 4), name, font=tag_font, fill=TITLE)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path, help="folder for the downloaded previews and font")
    parser.add_argument("out", type=Path)
    parser.add_argument("--cjk-font", default=CJK_DEFAULT, help="Noto Sans CJK .ttc for the Chinese subtitle")
    args = parser.parse_args()
    download(args.cache)
    build(args.cache, args.cjk_font).save(args.out, optimize=True)
    print(args.out, f"{args.out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
