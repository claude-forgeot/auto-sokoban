"""Helpers de layout proportionnel pour le resize adaptatif (R2).

Principe : chaque scene definit ses positions/tailles dans une resolution de
reference (800x600) puis utilise ces helpers pour les rescale vers la taille
ecran courante.
"""

from __future__ import annotations

import pygame

# Resolution de reference utilisee pour definir les layouts des scenes.
BASE_W = 800
BASE_H = 600

# Taille minimale acceptee (clamp VIDEORESIZE).
MIN_W = 640
MIN_H = 480


def scale_rect(
    base_rect: pygame.Rect,
    current_size: tuple[int, int],
    base_size: tuple[int, int] = (BASE_W, BASE_H),
) -> pygame.Rect:
    """Rescale un rect de base_size vers current_size (proportionnel)."""
    bw, bh = base_size
    cw, ch = current_size
    sx = cw / bw
    sy = ch / bh
    return pygame.Rect(
        int(round(base_rect.x * sx)),
        int(round(base_rect.y * sy)),
        max(1, int(round(base_rect.width * sx))),
        max(1, int(round(base_rect.height * sy))),
    )


def scale_font_size(base_size: int, current_h: int, base_h: int = BASE_H) -> int:
    """Rescale une taille de police selon le facteur vertical."""
    return max(8, int(round(base_size * current_h / base_h)))


def clamp_window_size(w: int, h: int) -> tuple[int, int]:
    """Clamp la taille de fenetre au minimum acceptable."""
    return (max(MIN_W, w), max(MIN_H, h))
