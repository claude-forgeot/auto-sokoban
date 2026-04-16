"""Tests unitaires pour solver/bfs.py."""

from game.board import Board
from solver.bfs import BFS

# Niveau simple : 1 caisse, 3 coups
LEVEL_SIMPLE = """\
######
#    #
# @$ #
#  . #
#    #
######"""

# Niveau deja gagne
LEVEL_WON = """\
####
#* #
# @#
####"""

# Niveau minimal : pousser une caisse vers le haut
LEVEL_PUSH_UP = """\
####
# .#
# $#
# @#
####"""

# Niveau impossible (caisse coincee dans un coin)
LEVEL_IMPOSSIBLE = """\
#####
#$  #
#  .#
# @ #
#####"""


class TestBFS:
    def test_solve_simple(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        solver = BFS()
        result = solver.solve(board.state, "simple")
        assert result.found
        assert result.algo_name == "BFS"
        assert result.level_name == "simple"
        assert result.solution_length > 0
        assert result.total_nodes_explored > 0
        assert result.time_ms >= 0

    def test_solution_is_valid(self):
        """Verifie que la solution retournee mene bien a la victoire."""
        board = Board.from_xsb(LEVEL_SIMPLE)
        solver = BFS()
        result = solver.solve(board.state, "simple")
        assert result.found
        # Le dernier etat doit etre gagnant
        assert result.steps[-1].state_snapshot.is_won()

    def test_already_won(self):
        board = Board.from_xsb(LEVEL_WON)
        solver = BFS()
        result = solver.solve(board.state, "won")
        assert result.found
        assert result.solution_length == 0

    def test_push_up(self):
        board = Board.from_xsb(LEVEL_PUSH_UP)
        solver = BFS()
        result = solver.solve(board.state, "push")
        assert result.found
        # Solution optimale : 1 coup (UP pousse la caisse sur la cible)
        assert result.solution_length == 1

    def test_impossible(self):
        board = Board.from_xsb(LEVEL_IMPOSSIBLE)
        solver = BFS()
        result = solver.solve(board.state, "impossible")
        assert not result.found
        assert result.solution_length == 0
        assert result.steps == ()
        assert result.total_nodes_explored > 0

    def test_optimality(self):
        """BFS doit trouver la solution la plus courte."""
        board = Board.from_xsb(LEVEL_PUSH_UP)
        solver = BFS()
        result = solver.solve(board.state, "optimal")
        assert result.found
        # Solution optimale pour PUSH_UP : 1 coup
        assert result.solution_length == 1

    def test_steps_have_snapshots(self):
        board = Board.from_xsb(LEVEL_PUSH_UP)
        solver = BFS()
        result = solver.solve(board.state, "snapshots")
        assert result.found
        for step in result.steps:
            assert step.state_snapshot is not None
            assert step.direction is not None
