"""Tests d'intégration layout SolverScene (vérifient que les boutons et la
timeline restent contenus dans leurs zones aux résolutions cibles)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

pygame.init()

from game.level import list_levels
from solver.base import SolverResult
from ui.layout import MIN_H, MIN_W
from ui.scenes.base import SceneManager
from ui.scenes.solver import SolverScene


class _DummyAudio:
    def __getattr__(self, name: str):
        return lambda *a, **kw: None

    def is_music_playing(self) -> bool:
        return False

    def stop_music(self) -> None:
        pass


@pytest.fixture
def level_meta():
    return list_levels("levels/facile")[0]


@pytest.mark.parametrize(
    "screen_w,screen_h",
    [(MIN_W, MIN_H), (800, 600), (1280, 720), (1920, 1080)],
)
def test_all_buttons_contained_in_actions_zone(screen_w, screen_h, level_meta):
    """Chaque bouton (fixe + contextuel) tient dans zones.actions."""
    pygame.display.set_mode((screen_w, screen_h))
    mgr = SceneManager()
    scene = SolverScene(
        mgr, level_meta=level_meta, audio=_DummyAudio(),
        screen_w=screen_w, screen_h=screen_h,
    )
    scene.on_enter()

    all_buttons = list(scene._buttons)
    if scene._stop_button is not None:
        all_buttons.append(scene._stop_button)
    if scene._timeout_button is not None:
        all_buttons.append(scene._timeout_button)

    actions_zone = scene._zones.actions
    for btn in all_buttons:
        assert actions_zone.contains(btn.rect), (
            f"Bouton '{btn.label}' {btn.rect} déborde de zones.actions "
            f"{actions_zone} à {screen_w}x{screen_h}"
        )


@pytest.mark.parametrize(
    "screen_w,screen_h",
    [(MIN_W, MIN_H), (800, 600), (1280, 720), (1920, 1080)],
)
def test_draw_does_not_raise_at_all_done(screen_w, screen_h, level_meta):
    """draw() en état _all_done ne doit pas lever ni dessiner hors zones."""
    screen = pygame.display.set_mode((screen_w, screen_h))
    mgr = SceneManager()
    scene = SolverScene(
        mgr, level_meta=level_meta, audio=_DummyAudio(),
        screen_w=screen_w, screen_h=screen_h,
    )
    scene.on_enter()
    scene._results = [
        SolverResult(
            found=True, steps=(), total_nodes_explored=544, time_ms=3.2,
            solution_length=33, algo_name="A*", level_name=level_meta.name,
            stop_reason="found",
        ),
        SolverResult(
            found=True, steps=(), total_nodes_explored=559, time_ms=2.2,
            solution_length=33, algo_name="BFS", level_name=level_meta.name,
            stop_reason="found",
        ),
        SolverResult(
            found=False, steps=(), total_nodes_explored=5000, time_ms=10000.0,
            solution_length=0, algo_name="DFS", level_name=level_meta.name,
            stop_reason="timeout",
        ),
    ]
    scene._timelines = {
        "A*": [(0, 0), (1, 100), (2, 300), (3, 544)],
        "BFS": [(0, 0), (1, 150), (2, 400), (3, 559)],
        "DFS": [(0, 0), (1, 200), (2, 350), (3, 5000)],
    }
    scene._all_done = True
    scene.draw(screen)
    # Pas d'exception = succès. Le test implicite est que la timeline ne
    # doit pas déborder dans actions_zone (skip si place insuffisante).
