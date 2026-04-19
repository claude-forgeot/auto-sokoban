"""Palette de couleurs centralisee pour les scenes UI.

Toutes les couleurs utilisees par les scenes et widgets viennent d ici.
Les scenes peuvent importer sous un alias semantique local (BG_COLOR,
TITLE_COLOR, etc.) pour preserver la lisibilite dans le contexte.
"""

from __future__ import annotations

RGB = tuple[int, int, int]

BG_PRIMARY: RGB = (25, 25, 35)
BG_GAME_OVER: RGB = (20, 15, 15)

ACCENT_YELLOW: RGB = (255, 220, 80)
ACCENT_BLUE: RGB = (100, 180, 255)

SUCCESS_GREEN: RGB = (100, 255, 120)
DANGER_RED: RGB = (255, 100, 100)
DANGER_RED_GAME_OVER: RGB = (255, 80, 80)

TEXT_MAIN: RGB = (220, 220, 220)
TEXT_MUTED: RGB = (120, 120, 120)

SEPARATOR: RGB = (60, 60, 80)
