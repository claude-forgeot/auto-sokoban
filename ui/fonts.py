"""Chargement de polices avec cache et fallback SysFont."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame

_FONT_FILE = (
    Path(__file__).resolve().parent.parent / "assets" / "fonts" / "DejaVuSansMono.ttf"
)


@lru_cache(maxsize=64)
def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    if _FONT_FILE.exists():
        font = pygame.font.Font(str(_FONT_FILE), size)
        if bold:
            font.set_bold(True)
        return font
    return pygame.font.SysFont("monospace", size, bold=bold)
