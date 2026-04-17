"""Solveur A* pour Sokoban avec heuristique Manhattan admissible."""

from __future__ import annotations

import heapq
import queue
import threading
import time

from game.board import BoardState, Direction
from solver.base import Solver, SolverResult, SolverStep, timer


def _manhattan_heuristic(state: BoardState) -> int:
    """Somme des distances Manhattan : chaque caisse vers la cible la plus proche.

    Heuristique admissible (sous-estime toujours le cout reel)
    car chaque caisse doit parcourir au moins cette distance.
    """
    total = 0
    targets = list(state.targets)
    for br, bc in state.boxes:
        min_dist = min(abs(br - tr) + abs(bc - tc) for tr, tc in targets)
        total += min_dist
    return total


class AStar(Solver):
    """Solveur A* avec heuristique Manhattan. Garantit l'optimalite."""

    name = "A*"

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

        # (f, compteur, g, etat, chemin)
        counter = 0
        h = _manhattan_heuristic(initial)
        heap: list[tuple[int, int, int, BoardState, list[Direction]]] = [
            (h, counter, 0, initial, [])
        ]
        visited: dict[BoardState, int] = {initial: 0}
        nodes_explored = 0

        while heap:
            _, _, g, state, path = heapq.heappop(heap)

            if g > visited.get(state, float("inf")):
                continue

            nodes_explored += 1

            for direction in Direction:
                new_state = self.apply_move(state, direction)
                if new_state is None:
                    continue

                new_g = g + 1
                if new_g >= visited.get(new_state, float("inf")):
                    continue

                visited[new_state] = new_g
                new_path = path + [direction]

                if new_state.is_won():
                    steps = self.build_steps(initial, new_path, nodes_explored)
                    return True, steps, nodes_explored

                h = _manhattan_heuristic(new_state)
                counter += 1
                heapq.heappush(heap, (new_g + h, counter, new_g, new_state, new_path))

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

        counter = 0
        h = _manhattan_heuristic(initial)
        heap: list[tuple[int, int, int, BoardState, list[Direction]]] = [
            (h, counter, 0, initial, [])
        ]
        visited: dict[BoardState, int] = {initial: 0}
        nodes_explored = 0
        visit_counts: dict[tuple[int, int], int] = {}

        while heap:
            if cancel_event.is_set():
                return False, (), nodes_explored, visit_counts

            _, _, g, state, path = heapq.heappop(heap)

            if g > visited.get(state, float("inf")):
                continue

            nodes_explored += 1
            pos = state.player
            visit_counts[pos] = visit_counts.get(pos, 0) + 1

            if nodes_explored % 50 == 0:
                self._report_progress(
                    progress_queue, nodes_explored, start_time,
                    frontier_size=len(heap),
                    current_depth=g,
                    visit_counts=visit_counts,
                )

            for direction in Direction:
                new_state = self.apply_move(state, direction)
                if new_state is None:
                    continue

                new_g = g + 1
                if new_g >= visited.get(new_state, float("inf")):
                    continue

                visited[new_state] = new_g
                new_path = path + [direction]

                if new_state.is_won():
                    steps = self.build_steps(initial, new_path, nodes_explored)
                    return True, steps, nodes_explored, visit_counts

                h = _manhattan_heuristic(new_state)
                counter += 1
                heapq.heappush(heap, (new_g + h, counter, new_g, new_state, new_path))

        return False, (), nodes_explored, visit_counts

