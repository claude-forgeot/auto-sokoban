"""Tests pour les helpers de layout (ui/layout.py)."""

import pygame

from ui.layout import SolverZones, compute_solver_zones


class TestSolverZones:
    """Tests du dataclass SolverZones."""

    def test_fields_are_rects(self) -> None:
        zones = SolverZones(
            title=pygame.Rect(0, 0, 100, 40),
            board=pygame.Rect(0, 40, 60, 60),
            metrics=pygame.Rect(60, 40, 40, 30),
            actions=pygame.Rect(60, 70, 40, 30),
        )
        assert isinstance(zones.title, pygame.Rect)
        assert isinstance(zones.board, pygame.Rect)
        assert isinstance(zones.metrics, pygame.Rect)
        assert isinstance(zones.actions, pygame.Rect)
