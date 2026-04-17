"""Solveur BFS (Breadth-First Search) pour Sokoban."""

from __future__ import annotations

import queue
import threading
import time
from collections import deque

from game.board import BoardState, Direction
from solver.base import Solver, SolverResult, SolverStep, timer


class BFS(Solver):
    """Solveur BFS. Garantit la solution optimale en nombre de mouvements."""

    name = "BFS"

    def solve(self, initial: BoardState, level_name: str = "") -> SolverResult:
        with timer() as t:
            result = self._search(initial, level_name)
        return SolverResult(
            found=result[0],
            steps=result[1],
            total_nodes_explored=result[2],
            time_ms=t(),
            solution_length=len(result[1]),
            algo_name=self.name,
            level_name=level_name,
        )

    def _search(
        self, initial: BoardState, level_name: str
    ) -> tuple[bool, tuple[SolverStep, ...], int]:
        if initial.is_won():
            return True, (), 0

        visited: set[BoardState] = {initial}
        # File : (etat courant, chemin de directions)
        queue: deque[tuple[BoardState, list[Direction]]] = deque()
        queue.append((initial, []))
        nodes_explored = 0

        while queue:
            state, path = queue.popleft()
            nodes_explored += 1

            for direction in Direction:
                new_state = self.apply_move(state, direction)
                if new_state is None or new_state in visited:
                    continue

                visited.add(new_state)
                new_path = path + [direction]

                if new_state.is_won():
                    steps = self.build_steps(initial, new_path, nodes_explored)
                    return True, steps, nodes_explored

                queue.append((new_state, new_path))

        return False, (), nodes_explored

    def _search_async(
        self,
        initial: BoardState,
        level_name: str,
        progress_queue: queue.Queue,
        cancel_event: threading.Event,
        start_time: float,
    ) -> tuple[bool, tuple[SolverStep, ...], int, dict[tuple[int, int], int]]:
        if initial.is_won():
            return True, (), 0, {}

        visited: set[BoardState] = {initial}
        frontier: deque[tuple[BoardState, list[Direction]]] = deque()
        frontier.append((initial, []))
        nodes_explored = 0
        visit_counts: dict[tuple[int, int], int] = {}

        while frontier:
            if cancel_event.is_set():
                return False, (), nodes_explored, visit_counts

            state, path = frontier.popleft()
            nodes_explored += 1
            pos = state.player
            visit_counts[pos] = visit_counts.get(pos, 0) + 1

            if nodes_explored % 50 == 0:
                self._report_progress(
                    progress_queue, nodes_explored, start_time,
                    frontier_size=len(frontier),
                    current_depth=len(path),
                    visit_counts=visit_counts,
                )

            for direction in Direction:
                new_state = self.apply_move(state, direction)
                if new_state is None or new_state in visited:
                    continue

                visited.add(new_state)
                new_path = path + [direction]

                if new_state.is_won():
                    steps = self.build_steps(initial, new_path, nodes_explored)
                    return True, steps, nodes_explored, visit_counts

                frontier.append((new_state, new_path))

        return False, (), nodes_explored, visit_counts

