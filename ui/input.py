"""Gestion des entrées clavier et boutons Pygame."""

from __future__ import annotations

from enum import Enum, auto

import pygame


class Action(Enum):
    """Actions sémantiques du jeu, découplées des touches physiques."""

    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    UNDO = auto()
    RESET = auto()
    SOLVE = auto()
    QUIT = auto()
    BACK_MENU = auto()
    PLAY = auto()
    RANKING = auto()
    PAUSE = auto()


_KEY_MAP: dict[int, Action] = {
    pygame.K_UP: Action.MOVE_UP,
    pygame.K_DOWN: Action.MOVE_DOWN,
    pygame.K_LEFT: Action.MOVE_LEFT,
    pygame.K_RIGHT: Action.MOVE_RIGHT,
    pygame.K_z: Action.MOVE_UP,
    pygame.K_s: Action.MOVE_DOWN,
    pygame.K_q: Action.MOVE_LEFT,
    pygame.K_d: Action.MOVE_RIGHT,
    pygame.K_u: Action.UNDO,
    pygame.K_BACKSPACE: Action.UNDO,
    pygame.K_r: Action.RESET,
    pygame.K_F5: Action.SOLVE,
    pygame.K_ESCAPE: Action.QUIT,
    pygame.K_SPACE: Action.PAUSE,
}


def poll_events(buttons: list[Button] | None = None) -> list[Action]:
    """Consomme les événements Pygame et retourne les actions correspondantes.

    Gère aussi les clics sur les ``Button`` fournis (hover + click).
    ``QUIT`` est émis à la fermeture de la fenêtre.
    """
    actions: list[Action] = []
    mouse_pos = pygame.mouse.get_pos()

    if buttons:
        for btn in buttons:
            btn.hovered = btn.rect.collidepoint(mouse_pos)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            actions.append(Action.QUIT)

        elif event.type == pygame.KEYDOWN:
            action = _KEY_MAP.get(event.key)
            if action is not None:
                actions.append(action)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if buttons:
                for btn in buttons:
                    if btn.rect.collidepoint(event.pos):
                        actions.append(btn.action)
                        break

    return actions


class Button:
    """Bouton cliquable avec rendu, hover et action associée."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        action: Action,
        *,
        font: pygame.font.Font | None = None,
        color: tuple[int, int, int] = (60, 60, 60),
        hover_color: tuple[int, int, int] = (90, 90, 90),
        text_color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        self.rect = rect
        self.label = label
        self.action = action
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.hovered = False

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine le bouton sur la surface donnée."""
        bg = self.hover_color if self.hovered else self.color
        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        pygame.draw.rect(surface, self.text_color, self.rect, width=1, border_radius=4)

        font = self.font or pygame.font.SysFont("monospace", 18)
        text_surf = font.render(self.label, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
