"""Panneau de metriques et tableau comparatif des solveurs."""

from __future__ import annotations

import pygame

from solver.base import SolverResult

# Couleurs
COLOR_BG = (30, 30, 40)
COLOR_TEXT = (220, 220, 220)
COLOR_HEADER = (100, 180, 255)
COLOR_BEST = (100, 255, 120)
COLOR_WORST = (255, 100, 100)
COLOR_SEPARATOR = (60, 60, 80)


class MetricsPanel:
    """Affiche les metriques d'un solveur et le tableau comparatif."""

    def __init__(self, width: int = 400, font_size: int = 16) -> None:
        self.width = width
        self.font_size = font_size
        self._font: pygame.font.Font | None = None
        self._result: SolverResult | None = None

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", self.font_size)
        return self._font

    def update(self, result: SolverResult) -> None:
        """Met a jour le resultat courant."""
        self._result = result

    def render(self) -> pygame.Surface:
        """Retourne une Surface avec les metriques du resultat courant."""
        font = self._get_font()
        line_h = self.font_size + 4
        height = line_h * 8
        surface = pygame.Surface((self.width, height))
        surface.fill(COLOR_BG)

        if self._result is None:
            text = font.render("Aucune resolution en cours", True, COLOR_TEXT)
            surface.blit(text, (10, 10))
            return surface

        r = self._result
        lines = [
            (f"Algorithme : {r.algo_name}", COLOR_HEADER),
            (f"Niveau     : {r.level_name}", COLOR_TEXT),
            (f"Resultat   : {'Resolu' if r.found else 'Echec'}", COLOR_BEST if r.found else COLOR_WORST),
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
        """Retourne une Surface avec le tableau comparatif BFS/DFS/A*."""
        font = self._get_font()
        line_h = self.font_size + 6
        height = line_h * (len(results) + 3)
        surface = pygame.Surface((self.width, height))
        surface.fill(COLOR_BG)

        if not results:
            text = font.render("Aucun resultat", True, COLOR_TEXT)
            surface.blit(text, (10, 10))
            return surface

        # En-tete
        header = f"{'Algo':<6} {'Coups':>6} {'Noeuds':>8} {'Temps':>10}"
        rendered = font.render(header, True, COLOR_HEADER)
        surface.blit(rendered, (10, 4))

        # Separateur
        y = line_h + 2
        pygame.draw.line(surface, COLOR_SEPARATOR, (10, y), (self.width - 10, y))
        y += 4

        # Identifier les meilleurs
        found_results = [r for r in results if r.found]
        best_coups = min((r.solution_length for r in found_results), default=0)
        best_temps = min((r.time_ms for r in found_results), default=0.0)
        best_noeuds = min((r.total_nodes_explored for r in found_results), default=0)

        for r in results:
            if not r.found:
                line = f"{r.algo_name:<6} {'echec':>6} {r.total_nodes_explored:>8} {r.time_ms:>9.1f}ms"
                rendered = font.render(line, True, COLOR_WORST)
            else:
                coups_color = COLOR_BEST if r.solution_length == best_coups else COLOR_TEXT
                temps_color = COLOR_BEST if r.time_ms == best_temps else COLOR_TEXT
                noeuds_color = COLOR_BEST if r.total_nodes_explored == best_noeuds else COLOR_TEXT

                # Rendu par segments pour colorer chaque colonne
                x = 10
                parts = [
                    (f"{r.algo_name:<6} ", COLOR_TEXT),
                    (f"{r.solution_length:>6} ", coups_color),
                    (f"{r.total_nodes_explored:>8} ", noeuds_color),
                    (f"{r.time_ms:>9.1f}ms", temps_color),
                ]
                for text, color in parts:
                    rendered = font.render(text, True, color)
                    surface.blit(rendered, (x, y))
                    x += rendered.get_width()

                y += line_h
                continue

            surface.blit(rendered, (10, y))
            y += line_h

        return surface
