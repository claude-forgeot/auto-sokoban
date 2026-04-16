"""Tests unitaires pour solver/a_star.py."""

from game.board import Board
from solver.a_star import AStar
from solver.bfs import BFS

LEVEL_PUSH_UP = """\
####
# .#
# $#
# @#
####"""

LEVEL_WON = """\
####
#* #
# @#
####"""

LEVEL_SIMPLE = """\
######
#    #
# @$ #
#  . #
#    #
######"""

LEVEL_MEDIUM = """\
  #####
###   #
# . # #
# $$  #
#.  ###
# $   #
# . @ #
#######"""


class TestAStar:
    def test_solve_simple(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        solver = AStar()
        result = solver.solve(board.state, "simple")
        assert result.found
        assert result.algo_name == "A*"
        assert result.solution_length > 0

    def test_solution_is_valid(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        solver = AStar()
        result = solver.solve(board.state, "simple")
        assert result.found
        assert result.steps[-1].state_snapshot.is_won()

    def test_already_won(self):
        board = Board.from_xsb(LEVEL_WON)
        solver = AStar()
        result = solver.solve(board.state, "won")
        assert result.found
        assert result.solution_length == 0

    def test_optimal_matches_bfs(self):
        """A* doit trouver la meme longueur de solution que BFS (les deux sont optimaux)."""
        board = Board.from_xsb(LEVEL_SIMPLE)
        bfs_result = BFS().solve(board.state, "bfs")
        astar_result = AStar().solve(board.state, "astar")
        assert astar_result.found
        assert astar_result.solution_length == bfs_result.solution_length

    def test_optimal_matches_bfs_medium(self):
        """Verification d'optimalite sur un niveau plus complexe."""
        board = Board.from_xsb(LEVEL_MEDIUM)
        bfs_result = BFS().solve(board.state, "bfs")
        astar_result = AStar().solve(board.state, "astar")
        assert astar_result.found
        assert astar_result.solution_length == bfs_result.solution_length

    def test_fewer_nodes_than_bfs(self):
        """A* devrait explorer moins de noeuds que BFS grace a l'heuristique."""
        board = Board.from_xsb(LEVEL_MEDIUM)
        bfs_result = BFS().solve(board.state, "bfs")
        astar_result = AStar().solve(board.state, "astar")
        assert astar_result.total_nodes_explored <= bfs_result.total_nodes_explored

    def test_steps_have_snapshots(self):
        board = Board.from_xsb(LEVEL_PUSH_UP)
        solver = AStar()
        result = solver.solve(board.state, "snapshots")
        assert result.found
        for step in result.steps:
            assert step.state_snapshot is not None
            assert step.direction is not None
