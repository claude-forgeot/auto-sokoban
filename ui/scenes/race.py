"""Scene de course cote-a-cote : 3 algorithmes en parallele."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field

import pygame

from game.level import LevelMeta, load_level
from solver.a_star import AStar
from solver.base import Solver, SolverProgress, SolverResult
from solver.bfs import BFS
from solver.dfs import DFS
from ui.audio import AudioManager
from ui.fonts import load_font
from ui.layout import scale_font_size
from ui.input import Action, Button, poll_events
from ui.metrics_panel import MetricsPanel
from ui.renderer import Renderer
from ui.scenes.base import Scene, SceneManager

from ui.colors import (
    BG_PRIMARY as BG_COLOR,
    TEXT_MAIN as TEXT_COLOR,
    ACCENT_BLUE as HEADER_COLOR,
    ACCENT_YELLOW as STATUS_COLOR,
    SUCCESS_GREEN as DONE_COLOR,
    SEPARATOR as SEPARATOR_COLOR,
    DANGER_RED,
)

REPLAY_DELAY_MS = 250
COL_COUNT = 3


@dataclass
class LaneState:
    """Etat d'une colonne/algo dans la course."""

    solver: Solver
    thread: threading.Thread | None = None
    progress_queue: queue.Queue[SolverProgress] = field(default_factory=queue.Queue)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    result: SolverResult | None = None
    progress: SolverProgress | None = None
    replay_step: int = 0
    replay_timer: int = 0
    replaying: bool = False
    done: bool = False
    finish_order: int = 0


class RaceScene(Scene):
    """Course côte-à-côte de 3 algorithmes sur le même niveau."""

    def __init__(
        self,
        manager: SceneManager,
        level_meta: LevelMeta,
        audio: AudioManager | None = None,
        screen_w: int = 800,
        screen_h: int = 600,
    ) -> None:
        super().__init__(manager)
        self.level_meta = level_meta
        # MODIFICATION : Ajout du paramétrage audio dans le constructeur
        # Cela permet à la scene race d'accéder aux sons
        self.audio = audio
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.board = load_level(level_meta.path)
        self._initial_state = self.board.state
        self._header_h = 55
        self._board_y = self._header_h
        self._variant = hash(level_meta.name) % 3
        self._compute_layout(screen_w, screen_h)
        self._renderers = [Renderer(tile_size=self._tile_size, variant=self._variant) for _ in range(COL_COUNT)]

        self._lanes: list[LaneState] = [
            LaneState(solver=AStar()),
            LaneState(solver=BFS()),
            LaneState(solver=DFS(max_depth=200)),
        ]
        self._finish_counter = 0
        self._all_done = False
        self._metrics = MetricsPanel(
            width=self._col_w - 10,
            font_size=scale_font_size(16, self.screen_h),
        )

        self._font: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._buttons: list[Button] = []

    def _compute_layout(self, screen_w: int, screen_h: int) -> None:
        self._col_w = screen_w // COL_COUNT
        cols = self._initial_state.width
        rows = self._initial_state.height
        max_tile = min(36, (self._col_w - 20) // max(cols, 1), (screen_h - 160) // max(rows, 1))
        self._tile_size = max(12, max_tile)

    def _build_buttons(self) -> None:
        assert self._font is not None
        sy = self.screen_h / 600
        btn_w = max(160, int(160 * self.screen_w / 800))
        btn_h = max(32, int(32 * sy))
        x = self.screen_w // 2 - btn_w // 2
        y = self.screen_h - max(40, int(40 * sy))
        self._buttons = [
            Button(pygame.Rect(x, y, btn_w, btn_h), "RETOUR MENU",
                    Action.BACK_MENU, font=self._font,
                    color=(100, 40, 40), hover_color=(140, 60, 60)),
        ]

    def on_enter(self) -> None:
        self._font = load_font(scale_font_size(16, self.screen_h))
        self._font_small = load_font(scale_font_size(12, self.screen_h))
        self._build_buttons()

        if self.audio is not None:
            self.audio.play_race_start()

        self._start_race()

    def on_resize(self, new_w: int, new_h: int) -> None:
        self.screen_w = new_w
        self.screen_h = new_h
        self._compute_layout(new_w, new_h)
        self._renderers = [
            Renderer(tile_size=self._tile_size, variant=self._variant)
            for _ in range(COL_COUNT)
        ]
        self._metrics = MetricsPanel(
            width=self._col_w - 10,
            font_size=scale_font_size(16, self.screen_h),
        )
        if self._font is not None:
            self._build_buttons()

    def _start_race(self) -> None:
        """Lance les 3 solveurs en parallele."""
        initial = load_level(self.level_meta.path).state

        for lane in self._lanes:
            lane.progress_queue = queue.Queue()
            lane.cancel_event = threading.Event()
            lane.thread = threading.Thread(
                target=lane.solver.solve_async,
                args=(initial, self.level_meta.name, lane.progress_queue, lane.cancel_event),
                daemon=True,
            )
            lane.thread.start()

    def handle_events(self) -> None:
        actions = poll_events(self._buttons, audio=self.audio)
        for action in actions:
            if action == Action.QUIT:
                self._cancel_all()
                self.manager.quit()
            elif action == Action.BACK_MENU:
                self._cancel_all()
                # MODIFICATION : Arrêter les sons de la course et relancer la musique du menu
                if self.audio is not None:
                    self.audio.return_to_menu()
                from ui.scenes.menu import MenuScene
                self.manager.switch(MenuScene(
                    self.manager, screen_w=self.screen_w, screen_h=self.screen_h,
                ))
                return

    def _cancel_all(self) -> None:
        for lane in self._lanes:
            lane.cancel_event.set()

    def update(self) -> None:
        for lane in self._lanes:
            while not lane.progress_queue.empty():
                try:
                    progress = lane.progress_queue.get_nowait()
                except queue.Empty:
                    break

                if progress.finished and progress.result is not None:
                    lane.result = progress.result
                    lane.done = True
                    self._finish_counter += 1
                    lane.finish_order = self._finish_counter

                    # Replay auto si résolu
                    lane.replay_step = 0
                    lane.replay_timer = pygame.time.get_ticks()
                    lane.replaying = progress.result.found and len(progress.result.steps) > 0
                    lane.thread = None
                else:
                    lane.progress = progress

            # Replay pas-a-pas
            if lane.replaying and lane.result:
                now = pygame.time.get_ticks()
                if now - lane.replay_timer >= REPLAY_DELAY_MS:
                    lane.replay_timer = now
                    lane.replay_step += 1
                    if lane.replay_step >= len(lane.result.steps):
                        lane.replaying = False

        self._all_done = all(lane.done for lane in self._lanes)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_COLOR)
        assert self._font is not None
        assert self._font_small is not None

        # Titre
        title = f"Course : {self.level_meta.name}"
        title_surf = self._font.render(title, True, TEXT_COLOR)
        screen.blit(title_surf, (self.screen_w // 2 - title_surf.get_width() // 2, 4))

        for i, lane in enumerate(self._lanes):
            x = i * self._col_w
            y = 24

            # Separateur vertical
            if i > 0:
                pygame.draw.line(screen, SEPARATOR_COLOR, (x, 24), (x, self.screen_h - 50))

            # Nom algo
            algo_name = lane.solver.name
            color = DONE_COLOR if lane.done else HEADER_COLOR
            name_surf = self._font.render(algo_name, True, color)
            screen.blit(name_surf, (x + self._col_w // 2 - name_surf.get_width() // 2, y))

            # Ordre d'arrivée
            if lane.done and lane.finish_order > 0:
                order_text = f"#{lane.finish_order}"
                order_surf = self._font_small.render(order_text, True, DONE_COLOR)
                screen.blit(order_surf, (x + self._col_w - 30, y + 2))

            y = self._header_h

            # Plateau
            if lane.result and lane.result.found and lane.result.steps:
                step_idx = min(lane.replay_step, len(lane.result.steps) - 1)
                state = lane.result.steps[step_idx].state_snapshot
            else:
                state = self._initial_state

            board_surf = self._renderers[i].render(state)
            bw, bh = board_surf.get_size()
            bx = x + (self._col_w - bw) // 2
            screen.blit(board_surf, (bx, y))

            y += bh + 6

            # Compteurs live
            if lane.done and lane.result:
                r = lane.result
                status = "Résolu" if r.found else "Échec"
                status_color = DONE_COLOR if r.found else DANGER_RED
                lines = [
                    (f"{status}", status_color),
                    (f"Coups  : {r.solution_length}", TEXT_COLOR),
                    (f"Noeuds : {r.total_nodes_explored}", TEXT_COLOR),
                    (f"Temps  : {r.time_ms:.0f} ms", TEXT_COLOR),
                ]
            elif lane.progress:
                p = lane.progress
                lines = [
                    ("Résolution...", STATUS_COLOR),
                    (f"Noeuds : {p.nodes_explored}", TEXT_COLOR),
                    (f"Front. : {p.frontier_size}", TEXT_COLOR),
                    (f"Prof.  : {p.current_depth}", TEXT_COLOR),
                    (f"Temps  : {p.elapsed_ms:.0f} ms", TEXT_COLOR),
                ]
            else:
                lines = [("Démarrage...", STATUS_COLOR)]

            line_h = self._font_small.get_linesize()
            for text, color in lines:
                rendered = self._font_small.render(text, True, color)
                screen.blit(rendered, (x + 8, y))
                y += line_h

        # Tableau comparatif final
        if self._all_done:
            results = [lane.result for lane in self._lanes if lane.result is not None]
            if results:
                comp_surf = self._metrics.render_comparison(results)
                cw, ch = comp_surf.get_size()
                comp_y = self.screen_h - 50 - ch
                # Masque toute la bande horizontale sous les lanes pour eviter
                # le chevauchement visuel avec les stats/replay des lanes.
                band = pygame.Rect(0, comp_y - 8, self.screen_w, ch + 16)
                pygame.draw.rect(screen, BG_COLOR, band)
                pygame.draw.rect(screen, SEPARATOR_COLOR, band, width=1)
                screen.blit(comp_surf, (self.screen_w // 2 - cw // 2, comp_y))

        # Boutons
        for btn in self._buttons:
            btn.draw(screen)