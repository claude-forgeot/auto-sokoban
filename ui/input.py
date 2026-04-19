"""Gestion des entrées clavier et boutons Pygame."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame

from ui import colors

if TYPE_CHECKING:
    from ui.audio import AudioManager

RGB = tuple[int, int, int]

# Variantes Cottagecore : (fill, shadow, text). fill=None -> bouton ghost (transparent).
_BUTTON_VARIANTS: dict[str, tuple[RGB | None, RGB, RGB]] = {
    "primary": (colors.SAGE, colors.SAGE_DARK, (255, 255, 255)),
    "solve": (colors.OLIVE, colors.OLIVE_DARK, (255, 255, 255)),
    "race": (colors.TERRACOTTA, colors.TERRACOTTA_DARK, (255, 255, 255)),
    "rank": (colors.GOLD, colors.GOLD_DARK, (74, 58, 16)),
    "quit": (colors.BROWN, colors.BROWN_DARK, (255, 255, 255)),
    "ghost": (None, colors.OLIVE, colors.INK),
}


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
    RACE = auto()
    HEATMAP = auto()
    SPEED_UP = auto()
    SPEED_DOWN = auto()
    ABANDON = auto()
    STOP_SOLVER = auto()
    CYCLE_TIMEOUT = auto()
    SCROLL_UP = auto()
    SCROLL_DOWN = auto()
    EXPORT_PDF = auto()
    NOOP = auto()  # placeholder pour boutons routes par rect (onglets)


_KEY_MAP: dict[int, Action] = {
    pygame.K_UP: Action.MOVE_UP,
    pygame.K_DOWN: Action.MOVE_DOWN,
    pygame.K_LEFT: Action.MOVE_LEFT,
    pygame.K_RIGHT: Action.MOVE_RIGHT,
    pygame.K_z: Action.MOVE_UP,
    pygame.K_s: Action.MOVE_DOWN,
    pygame.K_q: Action.MOVE_LEFT,
    pygame.K_d: Action.MOVE_RIGHT,
    pygame.K_w: Action.MOVE_UP,
    pygame.K_a: Action.MOVE_LEFT,
    pygame.K_u: Action.UNDO,
    pygame.K_BACKSPACE: Action.UNDO,
    pygame.K_r: Action.RESET,
    pygame.K_F5: Action.SOLVE,
    pygame.K_ESCAPE: Action.BACK_MENU,
    pygame.K_SPACE: Action.PAUSE,
    pygame.K_h: Action.HEATMAP,
    pygame.K_PLUS: Action.SPEED_UP,
    pygame.K_KP_PLUS: Action.SPEED_UP,
    pygame.K_EQUALS: Action.SPEED_UP,
    pygame.K_MINUS: Action.SPEED_DOWN,
    pygame.K_KP_MINUS: Action.SPEED_DOWN,
    pygame.K_t: Action.CYCLE_TIMEOUT,
    pygame.K_PAGEUP: Action.SCROLL_UP,
    pygame.K_PAGEDOWN: Action.SCROLL_DOWN,
    pygame.K_F10: Action.ABANDON,
}


class PollResult:
    """Résultat de poll_events : actions, clics bruts, event resize eventuel."""

    __slots__ = ("actions", "clicks", "resize")

    def __init__(self) -> None:
        self.actions: list[Action] = []
        self.clicks: list[tuple[int, int]] = []
        self.resize: tuple[int, int] | None = None

    def __iter__(self):  # noqa: ANN204
        return iter(self.actions)

    def __bool__(self) -> bool:
        return bool(self.actions)


def poll_events(
    buttons: list[Button] | None = None,
    audio: AudioManager | None = None,
) -> PollResult:
    """Consomme les événements Pygame et retourne les actions correspondantes.

    Gère aussi les clics sur les ``Button`` fournis (hover + click).
    ``QUIT`` est émis à la fermeture de la fenêtre.
    Si *audio* est fourni, joue le SFX ``button`` lors d'un clic bouton.
    ``PollResult.clicks`` contient les positions (x, y) de tous les clics
    gauches non captés par un bouton.
    """
    result = PollResult()
    mouse_pos = pygame.mouse.get_pos()

    if buttons:
        for btn in buttons:
            btn.hovered = btn.rect.collidepoint(mouse_pos)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            result.actions.append(Action.QUIT)

        elif event.type == pygame.VIDEORESIZE:
            result.resize = (event.w, event.h)

        elif event.type == pygame.KEYDOWN:
            action = _KEY_MAP.get(event.key)
            if action is not None:
                result.actions.append(action)

        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                result.actions.append(Action.SCROLL_UP)
            elif event.y < 0:
                result.actions.append(Action.SCROLL_DOWN)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            matched = False
            if buttons:
                for btn in buttons:
                    if btn.rect.collidepoint(event.pos):
                        result.actions.append(btn.action)
                        if audio is not None:
                            audio.play_sfx("button")
                        matched = True
                        break
            if not matched:
                result.clicks.append(event.pos)

    return result


class Button:
    """Bouton cliquable Cottagecore (ombre portee plate + hover translate)."""

    SHADOW_OFFSET = 3
    SHADOW_OFFSET_PRESSED = 1
    HOVER_LIFT = 2
    BORDER_RADIUS = 10

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        action: Action,
        *,
        font: pygame.font.Font | None = None,
        variant: str | None = None,
        color: RGB | None = None,
        hover_color: RGB | None = None,
        text_color: RGB | None = None,
        shadow_color: RGB | None = None,
    ) -> None:
        self.rect = rect
        self.label = label
        self.action = action
        self.font = font
        self.variant = variant
        if variant is not None and variant in _BUTTON_VARIANTS:
            v_fill, v_shadow, v_text = _BUTTON_VARIANTS[variant]
            self.color = color if color is not None else v_fill
            self.shadow_color = shadow_color if shadow_color is not None else v_shadow
            self.text_color = text_color if text_color is not None else v_text
        else:
            self.color = color if color is not None else (60, 60, 60)
            self.shadow_color = shadow_color if shadow_color is not None else _darken(self.color or (60, 60, 60))
            self.text_color = text_color if text_color is not None else (255, 255, 255)
        # hover_color garde la retrocompat mais devient rarement utile : l'effet
        # Cottagecore repose sur translate + ombre, pas sur changement de teinte.
        self.hover_color = hover_color if hover_color is not None else self.color
        self.hovered = False
        self.pressed = False

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine bouton + ombre portee plate avec effets hover/pressed."""
        self.pressed = self.hovered and pygame.mouse.get_pressed()[0]

        draw_rect = self.rect.copy()
        if self.pressed:
            shadow_offset = self.SHADOW_OFFSET_PRESSED
            draw_rect.y += 1
        elif self.hovered:
            shadow_offset = self.SHADOW_OFFSET
            draw_rect.y -= self.HOVER_LIFT
        else:
            shadow_offset = self.SHADOW_OFFSET

        shadow_rect = draw_rect.move(0, shadow_offset)
        pygame.draw.rect(surface, self.shadow_color, shadow_rect, border_radius=self.BORDER_RADIUS)

        if self.color is not None:
            fill = self.hover_color if self.hovered else self.color
            pygame.draw.rect(surface, fill, draw_rect, border_radius=self.BORDER_RADIUS)
        pygame.draw.rect(
            surface, self.shadow_color, draw_rect,
            width=2, border_radius=self.BORDER_RADIUS,
        )

        if self.font is not None:
            font = self.font
        else:
            from ui.fonts import load_font
            font = load_font(18)
        text_surf = font.render(self.label, True, self.text_color)
        text_rect = text_surf.get_rect(center=draw_rect.center)
        surface.blit(text_surf, text_rect)


def _darken(rgb: RGB, factor: float = 0.6) -> RGB:
    return (int(rgb[0] * factor), int(rgb[1] * factor), int(rgb[2] * factor))
