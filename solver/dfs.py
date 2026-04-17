"""Solveur DFS (Depth-First Search) pour Sokoban."""

from __future__ import annotations

import queue
import threading
import time

from game.board import BoardState, Direction
from solver.base import Solver, SolverResult, SolverStep, timer


class DFS(Solver):
    """Solveur DFS avec pile explicite et limite de profondeur.

    Ne garantit PAS l'optimalite. Utilise comme contre-exemple pedagogique
    face a BFS.
    """

    name = "DFS"

    def __init__(self, max_depth: int = 200) -> None:
        self.max_depth = max_depth

    def solve(self, initial: BoardState, level_name: str = "") -> SolverResult:
        with timer() as t:
            result = self._search(initial)
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
        self, initial: BoardState
    ) -> tuple[bool, tuple[SolverStep, ...], int]:
        if initial.is_won():
            return True, (), 0

        visited: set[BoardState] = {initial}
        # Pile : (etat, chemin de directions, profondeur)
        stack: list[tuple[BoardState, list[Direction], int]] = [
            (initial, [], 0)
        ]
        nodes_explored = 0

        while stack:
            state, path, depth = stack.pop()
            nodes_explored += 1

            if depth >= self.max_depth:
                continue

            for direction in Direction:
                new_state = self.apply_move(state, direction)
                if new_state is None or new_state in visited:
                    continue

                visited.add(new_state)
                new_path = path + [direction]

                if new_state.is_won():
                    steps = self.build_steps(initial, new_path, nodes_explored)
                    return True, steps, nodes_explored

                stack.append((new_state, new_path, depth + 1))

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
        stack: list[tuple[BoardState, list[Direction], int]] = [
            (initial, [], 0)
        ]
        nodes_explored = 0
        visit_counts: dict[tuple[int, int], int] = {}

        while stack:
            if cancel_event.is_set():
                return False, (), nodes_explored, visit_counts

            state, path, depth = stack.pop()
            nodes_explored += 1
            pos = state.player
            visit_counts[pos] = visit_counts.get(pos, 0) + 1

            if nodes_explored % 50 == 0:
                self._report_progress(
                    progress_queue, nodes_explored, start_time,
                    frontier_size=len(stack),
                    current_depth=depth,
                    visit_counts=visit_counts,
                )

            if depth >= self.max_depth:
                continue

            for direction in Direction:
                new_state = self.apply_move(state, direction)
                if new_state is None or new_state in visited:
                    continue

                visited.add(new_state)
                new_path = path + [direction]

                if new_state.is_won():
                    steps = self.build_steps(initial, new_path, nodes_explored)
                    return True, steps, nodes_explored, visit_counts

                stack.append((new_state, new_path, depth + 1))

        return False, (), nodes_explored, visit_counts

