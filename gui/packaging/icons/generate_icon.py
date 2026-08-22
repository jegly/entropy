#!/usr/bin/env python3
"""Generate the Entropy app icon: a chunky pixel-art CRT showing random static.

The 32x32 grid below is the source of truth. Every shipped PNG is an exact
integer multiple of it and is upscaled nearest-neighbour, so the pixels stay
square instead of being resampled into mush by the icon theme at small sizes.

The static is drawn from a fixed seed, so re-running this reproduces the same
icon rather than churning the binary on every build.

    python3 generate_icon.py

Writes hicolor/<size>x<size>/apps/com.jegly.entropygui.png for each size.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

APP_ID = "com.jegly.entropygui"
GRID = 32
SIZES = (32, 64, 128, 256)
SEED = 0x5EED

# --- palette: C64 indigo, breadbin beige, and bright 80s phosphor ----------
BG_BANDS = ("#4a3690", "#403080", "#372a70", "#2e2360")  # top -> bottom
EDGE = "#1b1338"
OUTLINE = "#160f2e"
BODY = "#ded2b6"
BODY_HI = "#f4ecd8"
BODY_SH = "#a2926f"
BEZEL = "#8d7f60"
SCREEN = "#140b28"
LED = "#5cf98a"

# Weighted so the dark screen shows through as gaps -- reads as noise, not confetti.
STATIC = (
    ["#ff3d8b"] * 3
    + ["#ff8a2b"] * 3
    + ["#ffe14d"] * 3
    + ["#3ce8b0"] * 3
    + ["#35c8ff"] * 3
    + ["#b06bff"] * 3
    + ["#ffffff"] * 1
    + [SCREEN] * 4
)


def rgba(color: str) -> tuple[int, int, int, int]:
    h = color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def mix(color: str, other: str, amount: float) -> tuple[int, int, int, int]:
    """Blend `amount` of `other` into `color` (used for the scanlines)."""
    a, b = rgba(color), rgba(other)
    return tuple(round(a[i] + (b[i] - a[i]) * amount) for i in range(3)) + (255,)


def in_rounded(x: int, y: int, size: int, radius: int) -> bool:
    """Rounded-rect hit test on pixel centres, so the corners come out even."""
    cx = min(max(x + 0.5, radius), size - radius)
    cy = min(max(y + 0.5, radius), size - radius)
    dx, dy = x + 0.5 - cx, y + 0.5 - cy
    return dx * dx + dy * dy <= radius * radius


def build_grid() -> Image.Image:
    img = Image.new("RGBA", (GRID, GRID), (0, 0, 0, 0))
    px = img.load()

    def rect(x0: int, y0: int, x1: int, y1: int, color) -> None:
        fill = color if isinstance(color, tuple) else rgba(color)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < GRID and 0 <= y < GRID:
                    px[x, y] = fill

    # --- background: rounded square, banded indigo -------------------------
    radius = 5
    inside = [[in_rounded(x, y, GRID, radius) for x in range(GRID)] for y in range(GRID)]
    for y in range(GRID):
        band = BG_BANDS[min(y * len(BG_BANDS) // GRID, len(BG_BANDS) - 1)]
        for x in range(GRID):
            if inside[y][x]:
                px[x, y] = rgba(band)

    # Darken the outermost ring so the tile has a defined edge on any wallpaper.
    for y in range(GRID):
        for x in range(GRID):
            if not inside[y][x]:
                continue
            if any(
                not (0 <= x + dx < GRID and 0 <= y + dy < GRID and inside[y + dy][x + dx])
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                px[x, y] = rgba(EDGE)

    # --- monitor shell -----------------------------------------------------
    rect(3, 3, 28, 23, OUTLINE)
    rect(4, 4, 27, 22, BODY)
    rect(4, 4, 27, 4, BODY_HI)      # light from the top left
    rect(4, 4, 4, 22, BODY_HI)
    rect(27, 5, 27, 22, BODY_SH)
    rect(5, 22, 27, 22, BODY_SH)

    # --- screen ------------------------------------------------------------
    rect(6, 6, 25, 19, BEZEL)
    rect(7, 7, 24, 18, SCREEN)

    # 2x2 blocks of static: 9 across, 6 down.
    rng = random.Random(SEED)
    for by in range(6):
        for bx in range(9):
            x0, y0 = 7 + bx * 2, 7 + by * 2
            rect(x0, y0, x0 + 1, y0 + 1, rng.choice(STATIC))

    # CRT scanlines: pull every other row toward the screen black.
    for y in range(8, 19, 2):
        for x in range(7, 25):
            px[x, y] = mix("#%02x%02x%02x" % px[x, y][:3], SCREEN, 0.34)

    # --- front panel, neck, base ------------------------------------------
    rect(6, 21, 7, 21, LED)         # power light
    rect(20, 21, 24, 21, BODY_SH)   # brand strip

    rect(13, 24, 18, 26, BODY_SH)   # neck
    rect(13, 24, 13, 26, OUTLINE)
    rect(18, 24, 18, 26, OUTLINE)

    rect(9, 27, 22, 28, BODY)       # base
    rect(9, 28, 22, 28, OUTLINE)
    rect(9, 27, 9, 27, OUTLINE)
    rect(22, 27, 22, 27, OUTLINE)

    return img


def main() -> None:
    grid = build_grid()
    here = Path(__file__).resolve().parent
    for size in SIZES:
        if size % GRID:
            raise SystemExit(f"{size} is not an integer multiple of the {GRID}px grid")
        out_dir = here / "hicolor" / f"{size}x{size}" / "apps"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{APP_ID}.png"
        grid.resize((size, size), Image.NEAREST).save(out, optimize=True)
        print(f"wrote {out.relative_to(here)}")


if __name__ == "__main__":
    main()
