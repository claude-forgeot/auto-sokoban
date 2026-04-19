"""Palette de couleurs Cottagecore centralisee pour les scenes UI.

15 tokens semantiques (sage + or + terracotta) issus de `design/ui-mockup.md`
(direction Cottagecore validee 2026-04-19). Les scenes peuvent importer sous
un alias semantique local (BG_COLOR, TITLE_COLOR, etc.) pour preserver la
lisibilite dans le contexte.

Les alias legacy (ACCENT_YELLOW, SUCCESS_GREEN, etc.) pointent vers les
nouveaux tokens pour ne pas casser les imports nommes dans les scenes.
"""

from __future__ import annotations

RGB = tuple[int, int, int]

# 15 tokens Cottagecore

BG: RGB = (245, 234, 208)
PANEL: RGB = (251, 245, 230)
INK: RGB = (46, 59, 29)
SAGE: RGB = (107, 142, 35)
SAGE_DARK: RGB = (74, 107, 43)
OLIVE: RGB = (139, 115, 85)
OLIVE_DARK: RGB = (93, 75, 58)
TERRACOTTA: RGB = (192, 112, 64)
TERRACOTTA_DARK: RGB = (136, 74, 40)
GOLD: RGB = (212, 167, 58)
GOLD_DARK: RGB = (154, 120, 32)
BROWN: RGB = (139, 90, 60)
BROWN_DARK: RGB = (106, 68, 56)
CREAM: RGB = (236, 217, 168)
SEPARATOR: RGB = (139, 115, 85)

# Alias legacy -> tokens Cottagecore (backcompat imports nommes scenes)

BG_PRIMARY: RGB = BG
BG_GAME_OVER: RGB = BROWN
ACCENT_YELLOW: RGB = GOLD
ACCENT_BLUE: RGB = SAGE
SUCCESS_GREEN: RGB = SAGE
DANGER_RED: RGB = TERRACOTTA
DANGER_RED_GAME_OVER: RGB = TERRACOTTA_DARK
TEXT_MAIN: RGB = INK
TEXT_MUTED: RGB = OLIVE
