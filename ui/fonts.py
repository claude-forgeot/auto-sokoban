"""Chargement de polices avec cache et fallback SysFont."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame

_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

_LEGACY_FONT = _FONTS_DIR / "DejaVuSansMono.ttf"
_SERIF_UPRIGHT = _FONTS_DIR / "Fraunces.ttf"
_SERIF_ITALIC = _FONTS_DIR / "Fraunces-Italic.ttf"
_MONO_REGULAR = _FONTS_DIR / "IBMPlexMono-Regular.ttf"
_MONO_SEMIBOLD = _FONTS_DIR / "IBMPlexMono-SemiBold.ttf"


@lru_cache(maxsize=64)
def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    if _LEGACY_FONT.exists():
        font = pygame.font.Font(str(_LEGACY_FONT), size)
        if bold:
            font.set_bold(True)
        return font
    return pygame.font.SysFont("monospace", size, bold=bold)


@lru_cache(maxsize=64)
def load_serif(
    size: int, weight: str = "regular", italic: bool = False
) -> pygame.font.Font:
    path = _SERIF_ITALIC if italic else _SERIF_UPRIGHT
    if path.exists():
        font = pygame.font.Font(str(path), size)
        if weight == "bold":
            font.set_bold(True)
        return font
    return pygame.font.SysFont(
        "serif", size, bold=(weight == "bold"), italic=italic
    )


@lru_cache(maxsize=64)
def load_mono(size: int, bold: bool = False) -> pygame.font.Font:
    path = _MONO_SEMIBOLD if bold else _MONO_REGULAR
    if path.exists():
        return pygame.font.Font(str(path), size)
    return pygame.font.SysFont("monospace", size, bold=bold)
