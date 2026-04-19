"""Tests d'intégration layout RaceScene (vérifient que le bouton retour reste
contenu dans zones.actions et que draw() ne lève pas aux résolutions cibles)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

pygame.init()

from game.level import list_levels
from ui.layout import MIN_H, MIN_W
from ui.scenes.base import SceneManager
from ui.scenes.race import RaceScene


class _DummyAudio:
    def __getattr__(self, name: str):
        return lambda *a, **kw: None

    def is_music_playing(self) -> bool:
        return False

    def stop_music(self) -> None:
        pass

    def play_music(self, *a, **kw) -> None:
        pass

    def return_to_menu(self) -> None:
        pass


@pytest.fixture
def level_meta():
    return list_levels("levels/facile")[0]


@pytest.mark.parametrize(
    "screen_w,screen_h",
    [(MIN_W, MIN_H), (800, 600), (1280, 720), (1920, 1080)],
)
def test_back_button_inside_actions_zone(screen_w, screen_h, level_meta):
    """Le bouton RETOUR MENU tient dans zones.actions à toutes les résolutions."""
    pygame.display.set_mode((screen_w, screen_h))
    mgr = SceneManager()
    scene = RaceScene(
        mgr, level_meta=level_meta, audio=_DummyAudio(),
        screen_w=screen_w, screen_h=screen_h,
    )
    scene.on_enter()
    actions_zone = scene._zones.actions
    for btn in scene._buttons:
        assert actions_zone.contains(btn.rect), (
            f"Bouton '{btn.label}' {btn.rect} déborde de zones.actions "
            f"{actions_zone} à {screen_w}x{screen_h}"
        )
    scene._cancel_all()


@pytest.mark.parametrize(
    "screen_w,screen_h",
    [(MIN_W, MIN_H), (800, 600), (1280, 720), (1920, 1080)],
)
def test_draw_does_not_raise(screen_w, screen_h, level_meta):
    """draw() ne lève pas aux résolutions cibles, lanes sans progress ni result."""
    screen = pygame.display.set_mode((screen_w, screen_h))
    mgr = SceneManager()
    scene = RaceScene(
        mgr, level_meta=level_meta, audio=_DummyAudio(),
        screen_w=screen_w, screen_h=screen_h,
    )
    scene.on_enter()
    scene.draw(screen)
    scene._cancel_all()
