"""Genere code/assets/ui/bg_cottagecore.png (800x600).

Approximation Pygame du CSS du mockup :
  radial-gradient(ellipse 60% 40% at 20% 20%, rgba(168,184,114,0.33) 0%, transparent 60%),
  radial-gradient(ellipse 60% 40% at 80% 80%, rgba(212,147,77,0.22) 0%, transparent 60%),
  linear-gradient(135deg, BG 0%, CREAM 100%);

Script one-shot : relancer uniquement si la direction change. Le .png resultant
est commit dans assets/ui/.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import pygame

BG = (245, 234, 208)
CREAM = (236, 217, 168)
SAGE_LIGHT = (168, 184, 114)
TERRACOTTA_LIGHT = (212, 147, 77)

W, H = 800, 600

OUT = Path(__file__).resolve().parent.parent / "assets" / "ui" / "bg_cottagecore.png"


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _fill_linear_diagonal(surface: pygame.Surface) -> None:
    w, h = surface.get_size()
    diag_len = w + h
    for y in range(h):
        for x in range(w):
            t = (x + y) / diag_len
            surface.set_at((x, y), (
                _lerp(BG[0], CREAM[0], t),
                _lerp(BG[1], CREAM[1], t),
                _lerp(BG[2], CREAM[2], t),
            ))


def _blit_radial(
    surface: pygame.Surface,
    center: tuple[int, int],
    radii: tuple[int, int],
    color: tuple[int, int, int],
    peak_alpha: int,
) -> None:
    cx, cy = center
    rx, ry = radii
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    # 20 ellipses concentriques, du plus petit (alpha max) au plus grand (alpha 0).
    steps = 24
    for i in range(steps, 0, -1):
        t = i / steps
        alpha = int(peak_alpha * (1 - t))
        if alpha <= 0:
            continue
        w = int(rx * 2 * t)
        h = int(ry * 2 * t)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.ellipse(overlay, (*color, alpha), rect)
    surface.blit(overlay, (0, 0))


def main() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))

    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Generer en resolution reduite (200x150) pour accelerer le per-pixel, puis upscaler.
    small = pygame.Surface((200, 150))
    _fill_linear_diagonal(small)
    surface = pygame.transform.smoothscale(small, (W, H))

    _blit_radial(
        surface,
        center=(int(W * 0.20), int(H * 0.20)),
        radii=(int(W * 0.60), int(H * 0.40)),
        color=SAGE_LIGHT,
        peak_alpha=math.floor(0.33 * 255),
    )
    _blit_radial(
        surface,
        center=(int(W * 0.80), int(H * 0.80)),
        radii=(int(W * 0.60), int(H * 0.40)),
        color=TERRACOTTA_LIGHT,
        peak_alpha=math.floor(0.22 * 255),
    )

    pygame.image.save(surface, str(OUT))
    print(f"Ecrit : {OUT}")


if __name__ == "__main__":
    main()
