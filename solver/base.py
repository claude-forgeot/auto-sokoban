"""Classes de base pour les solveurs Sokoban."""

from __future__ import annotations

import queue
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Literal

from game.board import BoardState, Direction

StopReason = Literal["found", "exhausted", "timeout", "user_cancelled"]
DEFAULT_TIMEOUT_MS = 60_000


@dataclass(frozen=True)
class SolverStep:
    """Une etape de solution."""

    direction: Direction
    state_snapshot: BoardState
    nodes_explored_so_far: int


VisitCounts = dict[tuple[int, int], int]


@dataclass(frozen=True)
class SolverResult:
    """Resultat complet d'une resolution."""

    found: bool
    steps: tuple[SolverStep, ...]
    total_nodes_explored: int
    time_ms: float
    solution_length: int
    algo_name: str
    level_name: str
    visit_counts: VisitCounts = field(default_factory=dict, hash=False, compare=False)
    stop_reason: StopReason = "exhausted"


@dataclass(frozen=True)
class SolverProgress:
    """Message de progression envoyé par un solveur asynchrone."""

    algo_name: str
    nodes_explored: int
    elapsed_ms: float
    finished: bool
    result: SolverResult | None = None
    frontier_size: int = 0
    current_depth: int = 0
    visit_counts: VisitCounts = field(default_factory=dict, hash=False, compare=False)


class Solver(ABC):
    """Interface abstraite pour les solveurs."""

    name: str

    @abstractmethod
    def solve(
        self,
        initial: BoardState,
        level_name: str = "",
        max_nodes: int | None = None,
    ) -> SolverResult:
        """Resout le niveau depuis l'etat initial.

        max_nodes : plafond optionnel du nombre de noeuds explores,
        None = pas de limite. Protection pour les callers hors UI
        (tests, scripts) qui ne passent pas par solve_async.
        """
        ...

    @staticmethod
    def apply_move(state: BoardState, direction: Direction) -> BoardState | None:
        """Applique un mouvement et retourne le nouvel etat, ou None si invalide."""
        dr, dc = direction.delta
        pr, pc = state.player
        new_r, new_c = pr + dr, pc + dc
        new_pos = (new_r, new_c)

        if new_pos in state.walls:
            return None

        if new_pos in state.boxes:
            beyond = (new_r + dr, new_c + dc)
            if beyond in state.walls or beyond in state.boxes:
                return None
            new_boxes = (state.boxes - {new_pos}) | {beyond}
            return BoardState(
                walls=state.walls,
                targets=state.targets,
                boxes=new_boxes,
                player=new_pos,
                width=state.width,
                height=state.height,
            )

        return BoardState(
            walls=state.walls,
            targets=state.targets,
            boxes=state.boxes,
            player=new_pos,
            width=state.width,
            height=state.height,
        )

    @staticmethod
    def build_steps(
        initial: BoardState, directions: list[Direction], final_nodes: int
    ) -> tuple[SolverStep, ...]:
        """Reconstruit les SolverStep depuis le chemin de directions."""
        steps: list[SolverStep] = []
        state = initial
        for d in directions:
            next_state = Solver.apply_move(state, d)
            if next_state is None:
                raise ValueError(
                    f"build_steps: direction invalide {d} a l'etat {state}"
                )
            state = next_state
            steps.append(
                SolverStep(
                    direction=d,
                    state_snapshot=state,
                    nodes_explored_so_far=final_nodes,
                )
            )
        return tuple(steps)

    def _report_progress(
        self,
        progress_queue: queue.Queue[SolverProgress],
        nodes_explored: int,
        start_time: float,
        frontier_size: int = 0,
        current_depth: int = 0,
        visit_counts: VisitCounts | None = None,
    ) -> None:
        """Envoie un message de progression dans la queue."""
        elapsed = (time.perf_counter() - start_time) * 1000
        progress_queue.put(SolverProgress(
            algo_name=self.name,
            nodes_explored=nodes_explored,
            elapsed_ms=elapsed,
            finished=False,
            frontier_size=frontier_size,
            current_depth=current_depth,
            visit_counts=dict(visit_counts) if visit_counts else {},
        ))

    def solve_async(
        self,
        initial: BoardState,
        level_name: str,
        progress_queue: queue.Queue[SolverProgress],
        cancel_event: threading.Event,
        timeout_ms: int | None = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Résout le niveau et envoie la progression via la queue.

        timeout_ms : délai maximum avant arrêt automatique. None = pas de limite.
        """
        start = time.perf_counter()
        found, steps, nodes, visits, reason = self._search_async(
            initial, level_name, progress_queue, cancel_event, start, timeout_ms,
        )
        elapsed = (time.perf_counter() - start) * 1000
        result = SolverResult(
            found=found,
            steps=steps,
            total_nodes_explored=nodes,
            time_ms=elapsed,
            solution_length=len(steps),
            algo_name=self.name,
            level_name=level_name,
            visit_counts=visits,
            stop_reason=reason,
        )
        progress_queue.put(SolverProgress(
            algo_name=self.name,
            nodes_explored=nodes,
            elapsed_ms=elapsed,
            finished=True,
            result=result,
            visit_counts=visits,
        ))

    @abstractmethod
    def _search_async(
        self,
        initial: BoardState,
        level_name: str,
        progress_queue: queue.Queue[SolverProgress],
        cancel_event: threading.Event,
        start_time: float,
        timeout_ms: int | None,
    ) -> tuple[bool, tuple[SolverStep, ...], int, VisitCounts, StopReason]:
        """Version async de _search, avec progression, annulation et timeout."""
        ...


@contextmanager
def timer():
    """Context manager pour mesurer le temps en millisecondes.

    Usage:
        with timer() as t:
            ...
        elapsed = t()
    """
    start = time.perf_counter()
    elapsed = [0.0]

    def get_elapsed() -> float:
        return elapsed[0]

    try:
        yield get_elapsed
    finally:
        elapsed[0] = (time.perf_counter() - start) * 1000
