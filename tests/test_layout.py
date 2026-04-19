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

    def test_zones_are_disjoint(self) -> None:
        """Les 4 zones ne se chevauchent jamais (3 résolutions testées)."""
        for screen_w, screen_h in [(800, 600), (1280, 720), (1920, 1080)]:
            zones = compute_solver_zones(screen_w, screen_h)
            rects = [zones.title, zones.board, zones.metrics, zones.actions]
            for i, a in enumerate(rects):
                for b in rects[i + 1 :]:
                    assert not a.colliderect(b), (
                        f"Zones se chevauchent à {screen_w}x{screen_h}: {a} et {b}"
                    )

    def test_zones_cover_screen(self) -> None:
        """Union des zones == écran (aire totale)."""
        for screen_w, screen_h in [(800, 600), (1280, 720), (1920, 1080)]:
            zones = compute_solver_zones(screen_w, screen_h)
            total_area = sum(
                r.width * r.height
                for r in [zones.title, zones.board, zones.metrics, zones.actions]
            )
            screen_area = screen_w * screen_h
            assert total_area == screen_area, (
                f"À {screen_w}x{screen_h}: total={total_area} screen={screen_area}"
            )

    def test_panel_and_board_minimum_sizes(self) -> None:
        """panel_w >= 380 et board_w > 0 à toutes les résolutions >= MIN."""
        from ui.layout import MIN_H, MIN_W

        for screen_w, screen_h in [
            (MIN_W, MIN_H),
            (800, 600),
            (1920, 1080),
        ]:
            zones = compute_solver_zones(screen_w, screen_h)
            assert zones.metrics.width >= 380, (
                f"panel_w {zones.metrics.width} < 380 à {screen_w}x{screen_h}"
            )
            assert zones.board.width > 0, (
                f"board_w = {zones.board.width} à {screen_w}x{screen_h}"
            )

    def test_dimensions_at_hd_resolution(self) -> None:
        """À 1920x1080 (sy=1.8), les zones scalent correctement."""
        zones = compute_solver_zones(1920, 1080)
        # title_h = max(30, 40*1.8) = 72
        assert zones.title.height == 72
        # panel_w = max(380, 1920*0.30) = 576
        assert zones.metrics.width == 576
        # board_w = 1920 - 576 = 1344
        assert zones.board.width == 1344
        # actions_h = max(5*(63+10)+16, 1080*0.35) = max(381, 378) = 381
        assert zones.actions.height == 381
        # metrics_h = 1080 - 72 - 381 = 627
        assert zones.metrics.height == 627
