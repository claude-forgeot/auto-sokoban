"""Tests d'integration end-to-end : chargement XSB reel + 3 algos."""

from pathlib import Path

import pytest

from game.level import load_level
from solver.a_star import AStar
from solver.bfs import BFS
from solver.dfs import DFS

LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"

EASY_LEVELS = [
    LEVELS_DIR / "facile" / "microban_001.xsb",
    LEVELS_DIR / "facile" / "microban_002.xsb",
    LEVELS_DIR / "facile" / "tuto_01.xsb",
]


@pytest.fixture(params=[p for p in EASY_LEVELS if p.is_file()], ids=lambda p: p.name)
def easy_board(request):
    return load_level(request.param)


class TestThreeSolvers:
    def test_all_three_find_solution(self, easy_board):
        """BFS, DFS, A* trouvent tous une solution sur les niveaux faciles."""
        state = easy_board.state
        assert BFS().solve(state, "bfs").found
        assert DFS().solve(state, "dfs").found
        assert AStar().solve(state, "astar").found

    def test_bfs_and_astar_same_length(self, easy_board):
        """BFS et A* garantissent l'optimalite : meme longueur de solution."""
        state = easy_board.state
        bfs = BFS().solve(state, "bfs")
        astar = AStar().solve(state, "astar")
        assert bfs.found and astar.found
        assert bfs.solution_length == astar.solution_length

    def test_no_crash_on_all_easy_levels(self, easy_board):
        """Aucun solveur ne crashe sur un niveau facile reel."""
        state = easy_board.state
        for solver in (BFS(), DFS(), AStar()):
            result = solver.solve(state, "smoke")
            assert result.solution_length >= 0
            assert result.total_nodes_explored >= 0
            assert result.time_ms >= 0
