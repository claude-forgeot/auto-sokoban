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
        # actions_h = max(6*(35+6)+16, 600*0.35) = max(262, 210) = 262
        # metrics_h = 600 - 40 - 262 = 298
        assert zones.metrics == pygame.Rect(420, 40, 380, 298)
        assert zones.actions == pygame.Rect(420, 338, 380, 262)

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
        # actions_h = max(6*(63+10)+16, 1080*0.35) = max(454, 378) = 454
        assert zones.actions.height == 454
        # metrics_h = 1080 - 72 - 454 = 554
        assert zones.metrics.height == 554


class TestRaceZones:
    """Tests du dataclass RaceZones."""

    def test_fields_are_rects(self) -> None:
        from ui.layout import RaceZones

        zones = RaceZones(
            title=pygame.Rect(0, 0, 100, 40),
            lanes=pygame.Rect(0, 40, 100, 370),
            comparatif=pygame.Rect(0, 410, 100, 130),
            actions=pygame.Rect(0, 540, 100, 60),
        )
        assert isinstance(zones.title, pygame.Rect)
        assert isinstance(zones.lanes, pygame.Rect)
        assert isinstance(zones.comparatif, pygame.Rect)
        assert isinstance(zones.actions, pygame.Rect)

    def test_dimensions_at_base_resolution(self) -> None:
        """À 800x600 (sy=1.0), dimensions selon la formule du spec."""
        from ui.layout import compute_race_zones

        zones = compute_race_zones(800, 600)
        assert zones.title == pygame.Rect(0, 0, 800, 40)
        assert zones.lanes == pygame.Rect(0, 40, 800, 370)
        assert zones.comparatif == pygame.Rect(0, 410, 800, 130)
        assert zones.actions == pygame.Rect(0, 540, 800, 60)

    def test_zones_are_disjoint(self) -> None:
        """Les 4 zones ne se chevauchent jamais (3 résolutions testées)."""
        from ui.layout import compute_race_zones

        for screen_w, screen_h in [(800, 600), (1280, 720), (1920, 1080)]:
            zones = compute_race_zones(screen_w, screen_h)
            rects = [zones.title, zones.lanes, zones.comparatif, zones.actions]
            for i, a in enumerate(rects):
                for b in rects[i + 1 :]:
                    assert not a.colliderect(b), (
                        f"Zones se chevauchent à {screen_w}x{screen_h}: {a} et {b}"
                    )

    def test_zones_cover_screen(self) -> None:
        """Union des zones == écran (aire totale identique)."""
        from ui.layout import compute_race_zones

        for screen_w, screen_h in [(800, 600), (1280, 720), (1920, 1080)]:
            zones = compute_race_zones(screen_w, screen_h)
            total_area = sum(
                r.width * r.height
                for r in [zones.title, zones.lanes, zones.comparatif, zones.actions]
            )
            screen_area = screen_w * screen_h
            assert total_area == screen_area, (
                f"À {screen_w}x{screen_h}: total={total_area} screen={screen_area}"
            )

    def test_lanes_height_minimum(self) -> None:
        """À MIN_H=480, lanes_h doit rester >= 288 (garantie sous-zones lane).

        Calcul : 480 - title_h(32) - actions_h(50) - comp_h(110) = 288.
        """
        from ui.layout import MIN_H, MIN_W, compute_race_zones

        zones = compute_race_zones(MIN_W, MIN_H)
        assert zones.lanes.height >= 288, (
            f"lanes_h={zones.lanes.height} < 288 à {MIN_W}x{MIN_H}"
        )
        assert zones.comparatif.height >= 110, (
            f"comp_h={zones.comparatif.height} < 110 à {MIN_W}x{MIN_H}"
        )
        assert zones.title.height >= 30
        assert zones.actions.height >= 50

    def test_dimensions_at_hd_resolution(self) -> None:
        """À 1920x1080 (sy=1.8), les zones scalent correctement."""
        from ui.layout import compute_race_zones

        zones = compute_race_zones(1920, 1080)
        # title_h = max(30, 40*1.8) = 72
        assert zones.title.height == 72
        # actions_h = max(50, 60*1.8) = 108
        assert zones.actions.height == 108
        # comp_h = max(110, 130*1.8) = 234
        assert zones.comparatif.height == 234
        # lanes_h = 1080 - 72 - 108 - 234 = 666
        assert zones.lanes.height == 666
        # Full width at every band
        for rect in [zones.title, zones.lanes, zones.comparatif, zones.actions]:
            assert rect.width == 1920

    def test_lanes_divisible_by_three(self) -> None:
        """lanes.width // 3 * 3 reste dans la bande (reste absorbe par bord droit)."""
        from ui.layout import compute_race_zones

        for screen_w, screen_h in [(800, 600), (1280, 720), (1920, 1080)]:
            zones = compute_race_zones(screen_w, screen_h)
            lane_w = zones.lanes.width // 3
            # 3 lanes + reste (<= 2px) absorbe
            assert 3 * lane_w <= zones.lanes.width
            assert zones.lanes.width - 3 * lane_w <= 2, (
                f"Reste trop grand à {screen_w}x{screen_h}: {zones.lanes.width - 3*lane_w}"
            )
