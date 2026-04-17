"""Tests unitaires pour solver/base.py."""

import time

from game.board import BoardState, Direction
from solver.base import Solver, SolverResult, SolverStep, timer


class DummySolver(Solver):
    """Solveur factice pour tester l'ABC."""

    name = "Dummy"

    def solve(self, initial: BoardState, level_name: str = "") -> SolverResult:
        return SolverResult(
            found=False,
            steps=(),
            total_nodes_explored=0,
            time_ms=0.0,
            solution_length=0,
            algo_name=self.name,
            level_name=level_name,
        )

    def _search_async(self, initial, level_name, progress_queue, cancel_event, start_time, timeout_ms=None):
        return False, (), 0, {}, "exhausted"


class TestSolverStep:
    def test_frozen(self):
        state = BoardState(
            walls=frozenset(),
            targets=frozenset({(0, 0)}),
            boxes=frozenset({(0, 0)}),
            player=(1, 1),
            width=2,
            height=2,
        )
        step = SolverStep(
            direction=Direction.UP,
            state_snapshot=state,
            nodes_explored_so_far=5,
        )
        assert step.direction == Direction.UP
        assert step.nodes_explored_so_far == 5


class TestSolverResult:
    def test_not_found(self):
        r = SolverResult(
            found=False,
            steps=(),
            total_nodes_explored=100,
            time_ms=5.0,
            solution_length=0,
            algo_name="BFS",
            level_name="test",
        )
        assert not r.found
        assert r.steps == ()
        assert r.solution_length == 0

    def test_found(self):
        state = BoardState(
            walls=frozenset(),
            targets=frozenset({(0, 0)}),
            boxes=frozenset({(0, 0)}),
            player=(1, 1),
            width=2,
            height=2,
        )
        step = SolverStep(Direction.UP, state, 1)
        r = SolverResult(
            found=True,
            steps=(step,),
            total_nodes_explored=10,
            time_ms=1.5,
            solution_length=1,
            algo_name="DFS",
            level_name="lvl1",
        )
        assert r.found
        assert len(r.steps) == 1
        assert r.solution_length == 1


class TestSolverABC:
    def test_instantiation(self):
        solver = DummySolver()
        assert solver.name == "Dummy"

    def test_solve_returns_result(self):
        solver = DummySolver()
        state = BoardState(
            walls=frozenset(),
            targets=frozenset({(0, 0)}),
            boxes=frozenset({(0, 0)}),
            player=(1, 1),
            width=2,
            height=2,
        )
        result = solver.solve(state, "test_level")
        assert isinstance(result, SolverResult)
        assert result.algo_name == "Dummy"
        assert result.level_name == "test_level"


class TestTimer:
    def test_measures_time(self):
        with timer() as t:
            time.sleep(0.01)
        elapsed = t()
        assert elapsed >= 5  # au moins 5 ms (marge pour CI lent)
        assert elapsed < 500  # pas plus de 500 ms
