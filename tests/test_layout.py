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

    def test_dimensions_at_base_resolution(self) -> None:
        """À 800x600 (sy=1.0), dimensions calculées selon la formule du spec."""
        zones = compute_solver_zones(800, 600)
        # title_h = max(30, 40 * 1.0) = 40
        assert zones.title == pygame.Rect(0, 0, 800, 40)
        # panel_w = max(380, 800 * 0.30) = max(380, 240) = 380
        # board_w = 800 - 380 = 420
        assert zones.board == pygame.Rect(0, 40, 420, 560)
        # actions_h = max(5*(35+6)+16, 600*0.35) = max(221, 210) = 221
        # metrics_h = 600 - 40 - 221 = 339
        assert zones.metrics == pygame.Rect(420, 40, 380, 339)
        assert zones.actions == pygame.Rect(420, 379, 380, 221)
