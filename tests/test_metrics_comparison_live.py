"""Tests pour MetricsPanel.render_comparison_live (mix progress/result)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

pygame.init()

from solver.base import SolverProgress, SolverResult
from ui.metrics_panel import MetricsPanel


def _make_result(algo: str, coups: int = 24, nodes: int = 312, time_ms: float = 145.0):
    return SolverResult(
        found=True, steps=(), total_nodes_explored=nodes, time_ms=time_ms,
        solution_length=coups, algo_name=algo, level_name="test",
        stop_reason="found",
    )


def _make_progress(algo: str, nodes: int = 500, elapsed: float = 80.0):
    return SolverProgress(
        algo_name=algo, nodes_explored=nodes, elapsed_ms=elapsed,
        finished=False,
    )


class _FakeLane:
    """Stub de LaneState -- seul lane.result et lane.progress sont utilisés."""

    def __init__(self, result=None, progress=None):
        self.result = result
        self.progress = progress
        class _S: pass
        self.solver = _S()
        self.solver.name = (result.algo_name if result else
                             progress.algo_name if progress else "?")


def test_render_comparison_live_all_finished_returns_surface():
    """Quand toutes les lanes ont un résultat, rend un tableau complet."""
    pygame.display.set_mode((800, 600))
    panel = MetricsPanel(width=400, font_size=14)
    lanes = [
        _FakeLane(result=_make_result("A*", 24, 312, 145.0)),
        _FakeLane(result=_make_result("BFS", 28, 890, 220.0)),
        _FakeLane(result=_make_result("DFS", 40, 2100, 380.0)),
    ]
    surf = panel.render_comparison_live(lanes)
    assert isinstance(surf, pygame.Surface)
    assert surf.get_width() == 400
    assert surf.get_height() > 0


def test_render_comparison_live_mix_progress_and_result():
    """Une lane finie + deux en cours -- tout doit se rendre sans exception."""
    pygame.display.set_mode((800, 600))
    panel = MetricsPanel(width=400, font_size=14)
    lanes = [
        _FakeLane(result=_make_result("A*", 24, 312, 145.0)),
        _FakeLane(progress=_make_progress("BFS", 890, 80.0)),
        _FakeLane(progress=_make_progress("DFS", 1240, 80.0)),
    ]
    surf = panel.render_comparison_live(lanes)
    assert isinstance(surf, pygame.Surface)
    font = panel._get_font()
    expected_min_h = (font.get_linesize() + 4) * 5
    assert surf.get_height() >= expected_min_h


def test_render_comparison_live_no_progress_no_result():
    """Lanes non démarrées -- affiche des placeholders '—' partout."""
    pygame.display.set_mode((800, 600))
    panel = MetricsPanel(width=400, font_size=14)
    lanes = [_FakeLane(), _FakeLane(), _FakeLane()]
    surf = panel.render_comparison_live(lanes)
    assert isinstance(surf, pygame.Surface)


def test_render_comparison_live_failed_result():
    """Un résultat non trouvé doit s'afficher en rouge avec 'échec'."""
    pygame.display.set_mode((800, 600))
    panel = MetricsPanel(width=400, font_size=14)
    failed = SolverResult(
        found=False, steps=(), total_nodes_explored=5000, time_ms=10000.0,
        solution_length=0, algo_name="DFS", level_name="test",
        stop_reason="timeout",
    )
    lanes = [_FakeLane(result=failed)]
    surf = panel.render_comparison_live(lanes)
    assert isinstance(surf, pygame.Surface)
