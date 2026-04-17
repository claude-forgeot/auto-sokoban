"""Tests pour l'exécution asynchrone des solveurs."""

import queue
import threading

from game.board import Board, BoardState, Direction
from solver.a_star import AStar
from solver.base import Solver, SolverProgress, SolverResult, SolverStep
from solver.bfs import BFS
from solver.dfs import DFS

SMALL_LEVEL = """\
#####
#@$.#
#####
"""


class DummyAsyncSolver(Solver):
    """Solveur factice qui explore N noeuds pour tester l'infra async."""

    name = "Dummy"

    def solve(self, initial: BoardState, level_name: str = "") -> SolverResult:
        return SolverResult(
            found=False, steps=(), total_nodes_explored=0,
            time_ms=0.0, solution_length=0,
            algo_name=self.name, level_name=level_name,
        )

    def _search_async(self, initial, level_name, progress_queue, cancel_event, start_time, timeout_ms=None):
        nodes = 0
        visit_counts = {}
        for _ in range(120):
            if cancel_event.is_set():
                return False, (), nodes, visit_counts, "user_cancelled"
            nodes += 1
            if nodes % 50 == 0:
                self._report_progress(progress_queue, nodes, start_time)
        return False, (), nodes, visit_counts, "exhausted"


class TestSolveAsync:
    def _make_state(self):
        return BoardState(
            walls=frozenset({(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)}),
            targets=frozenset(),
            boxes=frozenset(),
            player=(1, 1),
            width=3, height=3,
        )

    def test_progress_sent(self):
        solver = DummyAsyncSolver()
        state = self._make_state()
        q = queue.Queue()
        cancel = threading.Event()

        solver.solve_async(state, "test", q, cancel)

        messages = []
        while not q.empty():
            messages.append(q.get_nowait())

        # 120 noeuds / 50 = 2 progress + 1 final = 3 messages
        assert len(messages) == 3
        assert not messages[0].finished
        assert messages[0].nodes_explored == 50
        assert not messages[1].finished
        assert messages[1].nodes_explored == 100
        assert messages[2].finished
        assert messages[2].result is not None

    def test_cancel_stops_solver(self):
        solver = DummyAsyncSolver()
        state = self._make_state()
        q = queue.Queue()
        cancel = threading.Event()
        cancel.set()  # annulation immédiate

        solver.solve_async(state, "test", q, cancel)

        messages = []
        while not q.empty():
            messages.append(q.get_nowait())

        # Seul le message final (finished=True)
        assert len(messages) == 1
        assert messages[0].finished
        assert not messages[0].result.found
        assert messages[0].nodes_explored == 0
        assert messages[0].result.stop_reason == "user_cancelled"

    def test_stop_reason_exhausted(self):
        """Dummy explore 120 noeuds puis termine sans solution."""
        solver = DummyAsyncSolver()
        state = self._make_state()
        q = queue.Queue()
        cancel = threading.Event()

        solver.solve_async(state, "test", q, cancel)

        final = list(q.queue)[-1]
        assert final.result.stop_reason == "exhausted"


class SlowSolver(Solver):
    """Solveur factice qui boucle avec sleep pour tester le timeout."""

    name = "Slow"

    def solve(self, initial, level_name=""):
        return SolverResult(
            found=False, steps=(), total_nodes_explored=0,
            time_ms=0.0, solution_length=0,
            algo_name=self.name, level_name=level_name,
        )

    def _search_async(self, initial, level_name, progress_queue, cancel_event, start_time, timeout_ms=None):
        import time as _time
        nodes = 0
        for _ in range(10_000):
            if cancel_event.is_set():
                return False, (), nodes, {}, "user_cancelled"
            if timeout_ms is not None and (_time.perf_counter() - start_time) * 1000 > timeout_ms:
                return False, (), nodes, {}, "timeout"
            nodes += 1
            _time.sleep(0.001)
        return False, (), nodes, {}, "exhausted"


class TestTimeoutReason:
    """Tests dedies a la raison 'timeout'."""

    def _empty_state(self):
        return BoardState(
            walls=frozenset({(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)}),
            targets=frozenset(),
            boxes=frozenset(),
            player=(1, 1),
            width=3, height=3,
        )

    def test_slow_solver_timeout_fires(self):
        """Un solveur qui boucle 10s avec timeout=50ms doit stopper en timeout."""
        state = self._empty_state()
        q = queue.Queue()
        cancel = threading.Event()

        SlowSolver().solve_async(state, "slow", q, cancel, timeout_ms=50)

        final = list(q.queue)[-1]
        assert final.finished
        assert not final.result.found
        assert final.result.stop_reason == "timeout"

    def test_timeout_none_no_limit(self):
        """timeout_ms=None ne doit jamais timeouter sur un petit solveur."""
        state = self._empty_state()
        q = queue.Queue()
        cancel = threading.Event()

        DummyAsyncSolver().solve_async(state, "test", q, cancel, timeout_ms=None)

        final = list(q.queue)[-1]
        assert final.result.stop_reason == "exhausted"


class TestBFSAsync:
    def test_progress_and_result(self):
        board = Board.from_xsb(SMALL_LEVEL)
        q = queue.Queue()
        cancel = threading.Event()

        solver = BFS()
        solver.solve_async(board.state, "small", q, cancel)

        messages = []
        while not q.empty():
            messages.append(q.get_nowait())

        # Au moins le message final
        assert len(messages) >= 1
        final = messages[-1]
        assert final.finished
        assert final.result.found
        assert final.result.algo_name == "BFS"

        # Les messages intermédiaires sont dans l'ordre croissant
        # et contiennent les metriques live
        for i in range(len(messages) - 1):
            assert not messages[i].finished
            assert messages[i].frontier_size >= 0
            assert messages[i].current_depth >= 0
            if i > 0:
                assert messages[i].nodes_explored > messages[i - 1].nodes_explored

    def test_solve_unchanged(self):
        """solve() classique retourne le même résultat qu'avant."""
        board = Board.from_xsb(SMALL_LEVEL)
        solver = BFS()
        result = solver.solve(board.state, "small")
        assert result.found
        assert result.algo_name == "BFS"
        assert result.solution_length > 0


class TestDFSAsync:
    def test_progress_and_result(self):
        board = Board.from_xsb(SMALL_LEVEL)
        q = queue.Queue()
        cancel = threading.Event()

        solver = DFS(max_depth=200)
        solver.solve_async(board.state, "small", q, cancel)

        messages = []
        while not q.empty():
            messages.append(q.get_nowait())

        assert len(messages) >= 1
        final = messages[-1]
        assert final.finished
        assert final.result.found
        assert final.result.algo_name == "DFS"

    def test_solve_unchanged(self):
        board = Board.from_xsb(SMALL_LEVEL)
        solver = DFS(max_depth=200)
        result = solver.solve(board.state, "small")
        assert result.found
        assert result.algo_name == "DFS"


class TestAStarAsync:
    def test_progress_and_result(self):
        board = Board.from_xsb(SMALL_LEVEL)
        q = queue.Queue()
        cancel = threading.Event()

        solver = AStar()
        solver.solve_async(board.state, "small", q, cancel)

        messages = []
        while not q.empty():
            messages.append(q.get_nowait())

        assert len(messages) >= 1
        final = messages[-1]
        assert final.finished
        assert final.result.found
        assert final.result.algo_name == "A*"

    def test_solve_unchanged(self):
        board = Board.from_xsb(SMALL_LEVEL)
        solver = AStar()
        result = solver.solve(board.state, "small")
        assert result.found
        assert result.algo_name == "A*"


class TestSolverProgress:
    def test_in_progress(self):
        p = SolverProgress(
            algo_name="BFS",
            nodes_explored=50,
            elapsed_ms=12.3,
            finished=False,
        )
        assert p.algo_name == "BFS"
        assert p.nodes_explored == 50
        assert not p.finished
        assert p.result is None
        assert p.frontier_size == 0
        assert p.current_depth == 0

    def test_progress_with_live_metrics(self):
        p = SolverProgress(
            algo_name="A*",
            nodes_explored=200,
            elapsed_ms=45.0,
            finished=False,
            frontier_size=150,
            current_depth=8,
        )
        assert p.frontier_size == 150
        assert p.current_depth == 8

    def test_finished_with_result(self):
        result = SolverResult(
            found=True,
            steps=(),
            total_nodes_explored=100,
            time_ms=25.0,
            solution_length=5,
            algo_name="BFS",
            level_name="test",
        )
        p = SolverProgress(
            algo_name="BFS",
            nodes_explored=100,
            elapsed_ms=25.0,
            finished=True,
            result=result,
        )
        assert p.finished
        assert p.result is not None
        assert p.result.found

    def test_frozen(self):
        p = SolverProgress("BFS", 10, 1.0, False)
        try:
            p.nodes_explored = 20
            assert False, "devrait lever FrozenInstanceError"
        except AttributeError:
            pass

    def test_visit_counts_default(self):
        p = SolverProgress("BFS", 10, 1.0, False)
        assert p.visit_counts == {}

    def test_visit_counts_populated(self):
        counts = {(1, 1): 5, (2, 3): 2}
        p = SolverProgress("A*", 100, 50.0, False, visit_counts=counts)
        assert p.visit_counts == {(1, 1): 5, (2, 3): 2}


class TestVisitCountsInSolvers:
    def test_bfs_visit_counts(self):
        board = Board.from_xsb(SMALL_LEVEL)
        q = queue.Queue()
        cancel = threading.Event()

        BFS().solve_async(board.state, "small", q, cancel)

        messages = []
        while not q.empty():
            messages.append(q.get_nowait())

        final = messages[-1]
        assert final.result.visit_counts
        assert all(isinstance(k, tuple) and len(k) == 2 for k in final.result.visit_counts)
        assert all(v > 0 for v in final.result.visit_counts.values())

    def test_dfs_visit_counts(self):
        board = Board.from_xsb(SMALL_LEVEL)
        q = queue.Queue()
        cancel = threading.Event()

        DFS(max_depth=200).solve_async(board.state, "small", q, cancel)

        final = list(q.queue)[-1]
        assert final.result.visit_counts

    def test_a_star_visit_counts(self):
        board = Board.from_xsb(SMALL_LEVEL)
        q = queue.Queue()
        cancel = threading.Event()

        AStar().solve_async(board.state, "small", q, cancel)

        final = list(q.queue)[-1]
        assert final.result.visit_counts
