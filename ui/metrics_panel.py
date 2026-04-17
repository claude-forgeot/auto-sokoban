"""Panneau de metriques et tableau comparatif des solveurs."""

from __future__ import annotations

import pygame

from solver.base import SolverProgress, SolverResult
from ui.fonts import load_font

# Couleurs
COLOR_BG = (30, 30, 40)
COLOR_TEXT = (220, 220, 220)
COLOR_HEADER = (100, 180, 255)
COLOR_BEST = (100, 255, 120)
COLOR_WORST = (255, 100, 100)
COLOR_SEPARATOR = (60, 60, 80)
COLOR_FLASH = (255, 220, 50)

FLASH_DURATION_MS = 400


class MetricsPanel:
    """Affiche les metriques d'un solveur et le tableau comparatif."""

    def __init__(self, width: int = 400, font_size: int = 16) -> None:
        self.width = width
        self.font_size = font_size
        self._font: pygame.font.Font | None = None
        self._result: SolverResult | None = None
        self._progress: SolverProgress | None = None
        self._prev_values: dict[str, int] = {}
        self._flash_times: dict[str, int] = {}

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = load_font(self.font_size)
        return self._font

    def update(self, result: SolverResult) -> None:
        """Met a jour le resultat courant."""
        self._result = result

    def update_progress(self, progress: SolverProgress) -> None:
        """Met a jour la progression live. Detecte les changements pour le flash."""
        now = pygame.time.get_ticks()
        metrics = {
            "nodes": progress.nodes_explored,
            "frontier": progress.frontier_size,
            "depth": progress.current_depth,
        }
        for key, value in metrics.items():
            if self._prev_values.get(key) != value:
                self._flash_times[key] = now
                self._prev_values[key] = value
        self._progress = progress

    def clear_progress(self) -> None:
        """Remet la progression live a zero."""
        self._progress = None
        self._prev_values.clear()
        self._flash_times.clear()

    def _flash_color(self, key: str) -> tuple[int, int, int]:
        """Retourne la couleur interpolee entre flash jaune et texte normal."""
        now = pygame.time.get_ticks()
        flash_time = self._flash_times.get(key)
        if flash_time is None:
            return COLOR_TEXT
        elapsed = now - flash_time
        if elapsed >= FLASH_DURATION_MS:
            return COLOR_TEXT
        t = elapsed / FLASH_DURATION_MS
        return (
            int(COLOR_FLASH[0] + (COLOR_TEXT[0] - COLOR_FLASH[0]) * t),
            int(COLOR_FLASH[1] + (COLOR_TEXT[1] - COLOR_FLASH[1]) * t),
            int(COLOR_FLASH[2] + (COLOR_TEXT[2] - COLOR_FLASH[2]) * t),
        )

    def render_progress(self) -> pygame.Surface:
        """Retourne une Surface avec les compteurs live pendant le calcul."""
        font = self._get_font()
        line_h = self.font_size + 4
        height = line_h * 8
        surface = pygame.Surface((self.width, height))
        surface.fill(COLOR_BG)

        if self._progress is None:
            text = font.render("En attente du solveur...", True, COLOR_TEXT)
            surface.blit(text, (10, 10))
            return surface

        p = self._progress

        header = font.render(f"[{p.algo_name}] Résolution...", True, COLOR_HEADER)
        surface.blit(header, (10, 4))

        lines = [
            ("nodes", f"Noeuds     : {p.nodes_explored}"),
            ("frontier", f"Frontière  : {p.frontier_size}"),
            ("depth", f"Profondeur : {p.current_depth}"),
        ]

        y = 4 + line_h
        for key, text in lines:
            color = self._flash_color(key)
            rendered = font.render(text, True, color)
            surface.blit(rendered, (10, y))
            y += line_h

        elapsed_text = f"Temps      : {p.elapsed_ms:.0f} ms"
        rendered = font.render(elapsed_text, True, COLOR_TEXT)
        surface.blit(rendered, (10, y))

        return surface

    def render(self) -> pygame.Surface:
        """Retourne une Surface avec les metriques du resultat courant."""
        font = self._get_font()
        line_h = self.font_size + 4
        height = line_h * 8
        surface = pygame.Surface((self.width, height))
        surface.fill(COLOR_BG)

        if self._result is None:
            text = font.render("Aucune résolution en cours", True, COLOR_TEXT)
            surface.blit(text, (10, 10))
            return surface

        r = self._result
        lines = [
            (f"Algorithme : {r.algo_name}", COLOR_HEADER),
            (f"Niveau     : {r.level_name}", COLOR_TEXT),
            (f"Résultat   : {'Résolu' if r.found else 'Échec'}", COLOR_BEST if r.found else COLOR_WORST),
            (f"Coups      : {r.solution_length}", COLOR_TEXT),
            (f"Noeuds     : {r.total_nodes_explored}", COLOR_TEXT),
            (f"Temps      : {r.time_ms:.1f} ms", COLOR_TEXT),
        ]

        y = 4
        for text, color in lines:
            rendered = font.render(text, True, color)
            surface.blit(rendered, (10, y))
            y += line_h

        return surface

    def render_comparison(self, results: list[SolverResult]) -> pygame.Surface:
        """Retourne une Surface avec le tableau comparatif + barres proportionnelles."""
        font = self._get_font()
        line_h = self.font_size + 6
        bar_h = 12
        bar_section_h = (bar_h + line_h) * len(results) + line_h
        table_h = line_h * (len(results) + 2)
        height = table_h + bar_section_h + 10
        surface = pygame.Surface((self.width, height))
        surface.fill(COLOR_BG)

        if not results:
            text = font.render("Aucun résultat", True, COLOR_TEXT)
            surface.blit(text, (10, 10))
            return surface

        # -- Tableau texte --
        header = f"{'Algo':<6} {'Coups':>6} {'Noeuds':>8} {'Temps':>10}"
        rendered = font.render(header, True, COLOR_HEADER)
        surface.blit(rendered, (10, 4))

        y = line_h + 2
        pygame.draw.line(surface, COLOR_SEPARATOR, (10, y), (self.width - 10, y))
        y += 4

        found_results = [r for r in results if r.found]
        best_coups = min((r.solution_length for r in found_results), default=0)
        best_temps = min((r.time_ms for r in found_results), default=0.0)
        best_noeuds = min((r.total_nodes_explored for r in found_results), default=0)

        for r in results:
            if not r.found:
                line = f"{r.algo_name:<6} {'échec':>6} {r.total_nodes_explored:>8} {r.time_ms:>9.1f}ms"
                rendered = font.render(line, True, COLOR_WORST)
                surface.blit(rendered, (10, y))
            else:
                x = 10
                parts = [
                    (f"{r.algo_name:<6} ", COLOR_TEXT),
                    (f"{r.solution_length:>6} ", COLOR_BEST if r.solution_length == best_coups else COLOR_TEXT),
                    (f"{r.total_nodes_explored:>8} ", COLOR_BEST if r.total_nodes_explored == best_noeuds else COLOR_TEXT),
                    (f"{r.time_ms:>9.1f}ms", COLOR_BEST if r.time_ms == best_temps else COLOR_TEXT),
                ]
                for text, color in parts:
                    rendered = font.render(text, True, color)
                    surface.blit(rendered, (x, y))
                    x += rendered.get_width()
            y += line_h

        # -- Barres proportionnelles (temps) --
        y += 6
        pygame.draw.line(surface, COLOR_SEPARATOR, (10, y), (self.width - 10, y))
        y += 6
        label = font.render("Temps :", True, COLOR_HEADER)
        surface.blit(label, (10, y))
        y += line_h

        max_time = max((r.time_ms for r in results), default=1.0) or 1.0
        bar_max_w = self.width - 80

        for r in results:
            ratio = r.time_ms / max_time
            bar_w = max(2, int(ratio * bar_max_w))
            if not r.found:
                bar_color = COLOR_WORST
            elif r.time_ms == best_temps:
                bar_color = COLOR_BEST
            else:
                bar_color = (220, 180, 50)

            name_surf = font.render(f"{r.algo_name:<4}", True, COLOR_TEXT)
            surface.blit(name_surf, (10, y))
            pygame.draw.rect(surface, bar_color, (60, y + 2, bar_w, bar_h), border_radius=2)

            time_label = font.render(f"{r.time_ms:.0f}ms", True, COLOR_TEXT)
            surface.blit(time_label, (65 + bar_w, y))
            y += bar_h + line_h

        return surface

    def render_timeline(
        self, timelines: dict[str, list[tuple[float, int]]], width: int = 0, height: int = 160,
    ) -> pygame.Surface:
        """Retourne une Surface avec le graphe temps vs noeuds par algo."""
        w = width or self.width
        font = self._get_font()
        surface = pygame.Surface((w, height))
        surface.fill(COLOR_BG)

        if not timelines:
            return surface

        # Titre
        title = font.render("Noeuds / Temps", True, COLOR_HEADER)
        surface.blit(title, (10, 2))

        # Zone graphe
        margin_left = 50
        margin_right = 10
        margin_top = 22
        margin_bottom = 20
        gw = w - margin_left - margin_right
        gh = height - margin_top - margin_bottom

        # Axes
        pygame.draw.line(surface, COLOR_SEPARATOR, (margin_left, margin_top), (margin_left, margin_top + gh))
        pygame.draw.line(surface, COLOR_SEPARATOR, (margin_left, margin_top + gh), (margin_left + gw, margin_top + gh))

        # Echelle
        all_points = [pt for pts in timelines.values() for pt in pts]
        if not all_points:
            return surface

        max_time = max(t for t, _ in all_points) or 1.0
        max_nodes = max(n for _, n in all_points) or 1

        # Couleurs par algo
        algo_colors: dict[str, tuple[int, int, int]] = {
            "A*": (100, 255, 120),
            "BFS": (100, 180, 255),
            "DFS": (255, 180, 80),
        }
        default_color = COLOR_TEXT

        for algo_name, points in timelines.items():
            if len(points) < 2:
                continue
            color = algo_colors.get(algo_name, default_color)
            screen_points = []
            for t_ms, nodes in points:
                sx = margin_left + int(t_ms / max_time * gw)
                sy = margin_top + gh - int(nodes / max_nodes * gh)
                screen_points.append((sx, sy))
            pygame.draw.lines(surface, color, False, screen_points, 2)

        # Legende
        lx = margin_left + 4
        ly = margin_top + 2
        for algo_name in timelines:
            color = algo_colors.get(algo_name, default_color)
            pygame.draw.line(surface, color, (lx, ly + 6), (lx + 14, ly + 6), 2)
            label = font.render(algo_name, True, color)
            surface.blit(label, (lx + 18, ly))
            lx += 60

        # Labels axes
        time_label = font.render(f"{max_time:.0f}ms", True, COLOR_TEXT)
        surface.blit(time_label, (margin_left + gw - time_label.get_width(), margin_top + gh + 2))
        node_label = font.render(f"{max_nodes}", True, COLOR_TEXT)
        surface.blit(node_label, (2, margin_top))

        return surface
