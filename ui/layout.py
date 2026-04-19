"""Helpers de layout proportionnel pour le resize adaptatif (R2).

Principe : chaque scene definit ses positions/tailles dans une resolution de
reference (800x600) puis utilise ces helpers pour les rescale vers la taille
ecran courante.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

# Resolution de reference utilisee pour definir les layouts des scenes.
BASE_W = 800
BASE_H = 600

# Taille minimale acceptee (clamp VIDEORESIZE).
MIN_W = 640
MIN_H = 480


@dataclass(frozen=True)
class SolverZones:
    """Zones nommées disjointes pour SolverScene.

    title  : bande haute (status + nom niveau)
    board  : zone gauche (plateau Sokoban)
    metrics: zone droite haute (tableau comparatif + timeline)
    actions: zone droite basse (boutons empilés)
    """

    title: pygame.Rect
    board: pygame.Rect
    metrics: pygame.Rect
    actions: pygame.Rect


@dataclass(frozen=True)
class RaceZones:
    """Zones nommées disjointes pour RaceScene.

    title      : bande haute (nom niveau)
    lanes      : bande centrale (3 colonnes de largeur égale)
    comparatif : bande basse live (Algo / Coups / Nœuds / Temps)
    actions    : footer (RETOUR MENU centré)
    """

    title: pygame.Rect
    lanes: pygame.Rect
    comparatif: pygame.Rect
    actions: pygame.Rect


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


def compute_solver_zones(screen_w: int, screen_h: int) -> SolverZones:
    """Decoupe l'ecran SolverScene en zones nommees disjointes.

    Regles :
    - title_h scale vertical (min 30px)
    - panel_w : 30% ecran, min 380px pour contenir MetricsPanel
    - actions_h : 35% ecran, min 5 slots boutons
    - metrics_h : reste de la hauteur (comp + timeline tiennent dedans)
    - board : tout l'espace gauche

    Garanties :
    - Les 4 zones sont disjointes (pas de chevauchement).
    - panel_w >= 380 (MetricsPanel.width = 380-20 = 360 OK pour comp).
    - board_w >= MIN_W - 380 = 260 (playable).
    """
    
    # Ajouter validations
    if screen_w < MIN_W or screen_h < MIN_H:
        raise ValueError(f"Screen too small: {screen_w}x{screen_h}, need {MIN_W}x{MIN_H}")
    sy = screen_h / BASE_H
    title_h = max(30, int(40 * sy))
    panel_w = max(380, int(screen_w * 0.30))
    btn_h = max(35, int(35 * sy))
    btn_spacing = max(6, int(6 * sy))
    actions_h = max(5 * (btn_h + btn_spacing) + 16, int(screen_h * 0.35))
    # Vérifier que board_w >= 0
    board_w = max(1, screen_w - panel_w)  # Forcer minimum 1px
    metrics_h = max(1, screen_h - title_h - actions_h)

    return SolverZones(
        title=pygame.Rect(0, 0, screen_w, title_h),
        board=pygame.Rect(0, title_h, board_w, screen_h - title_h),
        metrics=pygame.Rect(board_w, title_h, panel_w, metrics_h),
        actions=pygame.Rect(board_w, title_h + metrics_h, panel_w, actions_h),
    )


def compute_race_zones(screen_w: int, screen_h: int) -> RaceZones:
    """Decoupe l'ecran RaceScene en 4 bandes horizontales disjointes.

    Règles :
    - title_h scale vertical (min 30px, base 40)
    - actions_h scale vertical (min 50px, base 60) -- 1 bouton centré
    - comp_h scale vertical (min 110px, base 130) -- header + 3 lignes + padding
    - lanes_h : reste de la hauteur

    Garanties :
    - Les 4 zones sont disjointes (pas de chevauchement).
    - Union des zones couvre l'écran entier (pas de pixel perdu).
    - lanes_h >= 288 = 480 - 32 - 50 - 110 pour screen_h >= MIN_H = 480.
    """
    sy = screen_h / BASE_H
    title_h = max(30, int(40 * sy))
    actions_h = max(50, int(60 * sy))
    comp_h = max(110, int(130 * sy))
    lanes_h = screen_h - title_h - actions_h - comp_h

    return RaceZones(
        title=pygame.Rect(0, 0, screen_w, title_h),
        lanes=pygame.Rect(0, title_h, screen_w, lanes_h),
        comparatif=pygame.Rect(0, title_h + lanes_h, screen_w, comp_h),
        actions=pygame.Rect(0, title_h + lanes_h + comp_h, screen_w, actions_h),
    )
