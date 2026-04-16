"""Tests unitaires pour solver/dfs.py."""

from game.board import Board
from solver.bfs import BFS
from solver.dfs import DFS

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


class TestDFS:
    def test_solve_simple(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        solver = DFS()
        result = solver.solve(board.state, "simple")
        assert result.found
        assert result.algo_name == "DFS"
        assert result.solution_length > 0

    def test_solution_is_valid(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        solver = DFS()
        result = solver.solve(board.state, "simple")
        assert result.found
        assert result.steps[-1].state_snapshot.is_won()

    def test_already_won(self):
        board = Board.from_xsb(LEVEL_WON)
        solver = DFS()
        result = solver.solve(board.state, "won")
        assert result.found
        assert result.solution_length == 0

    def test_push_up(self):
        board = Board.from_xsb(LEVEL_PUSH_UP)
        solver = DFS()
        result = solver.solve(board.state, "push")
        assert result.found

    def test_not_optimal(self):
        """DFS ne garantit pas l'optimalite : solution >= BFS."""
        board = Board.from_xsb(LEVEL_SIMPLE)
        bfs_result = BFS().solve(board.state, "bfs")
        dfs_result = DFS().solve(board.state, "dfs")
        assert dfs_result.found
        assert dfs_result.solution_length >= bfs_result.solution_length

    def test_max_depth(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        solver = DFS(max_depth=1)
        result = solver.solve(board.state, "shallow")
        # Avec profondeur 1, ne peut pas resoudre un niveau de 3 coups
        assert not result.found

    def test_steps_have_snapshots(self):
        board = Board.from_xsb(LEVEL_PUSH_UP)
        solver = DFS()
        result = solver.solve(board.state, "snapshots")
        assert result.found
        for step in result.steps:
            assert step.state_snapshot is not None
            assert step.direction is not None
