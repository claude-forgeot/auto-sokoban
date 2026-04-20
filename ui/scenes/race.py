"""Scene de course cote-a-cote : 3 algorithmes en parallele."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import queue
import threading
from dataclasses import dataclass, field

import pygame

from game.level import LevelMeta, load_level
from solver.a_star import AStar
from solver.base import DEFAULT_TIMEOUT_MS, Solver, SolverProgress, SolverResult
from solver.bfs import BFS
from solver.dfs import DFS
from ui.audio import AudioManager
from ui.fonts import load_font, load_mono, load_serif
from ui.layout import BASE_H, BASE_W, compute_race_zones, scale_font_size
from ui.input import Action, Button, poll_events
from ui.metrics_panel import MetricsPanel
from ui.renderer import Renderer
from ui.scenes.base import Scene, SceneManager

from ui.colors import (
    BG as BG_COLOR,
    INK as TEXT_COLOR,
    SAGE_DARK as HEADER_COLOR,
    GOLD as STATUS_COLOR,
    SAGE as DONE_COLOR,
    SEPARATOR as SEPARATOR_COLOR,
    TERRACOTTA as DANGER_RED,
)

REPLAY_DELAY_MS = 250
COL_COUNT = 3
# Drain borne par frame pour eviter que le producteur (thread solver,
# _report_progress toutes les 50 iterations) n'inonde la main loop et fige
# la fenetre en l'empechant de traiter ses events systeme.
MAX_PROGRESS_DRAIN_PER_FRAME = 200


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
        timeout_ms: int | None = DEFAULT_TIMEOUT_MS,
    ) -> None:
        super().__init__(manager)
        self.level_meta = level_meta
        # MODIFICATION : Ajout du paramétrage audio dans le constructeur
        # Cela permet à la scene race d'accéder aux sons
        self.audio = audio
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._timeout_ms = timeout_ms

        self.board = load_level(level_meta.path)
        self._initial_state = self.board.state
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
            width=self._zones.comparatif.width - 20,
            font_size=scale_font_size(16, self.screen_h),
        )

        self._font: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._buttons: list[Button] = []

        # Toast confirmation
        self._toast_text: str | None = None
        self._toast_timer: int = 0
        self._toast_duration_ms: int = 3000

        # Timeline progression (algo_name -> list[(elapsed_ms, nodes)])
        self._timelines: dict[str, list[tuple[float, int]]] = {}

    def _compute_layout(self, screen_w: int, screen_h: int) -> None:
        self._zones = compute_race_zones(screen_w, screen_h)

        sy = screen_h / BASE_H
        self._lane_w = self._zones.lanes.width // 3
        self._header_h = max(32, int(32 * sy))
        self._stats_h = max(90, int(90 * sy))
        self._board_h = self._zones.lanes.height - self._header_h - self._stats_h

        cols = self._initial_state.width
        rows = self._initial_state.height
        max_tile = min(
            (self._lane_w - 20) // max(cols, 1),
            self._board_h // max(rows, 1),
        )
        self._tile_size = max(12, max_tile)

    def _build_buttons(self) -> None:
        assert self._font is not None
        actions = self._zones.actions
        btn_w = max(140, int(140 * self.screen_w / BASE_W))
        btn_h = max(32, int(32 * self.screen_h / BASE_H))
        gap = max(10, int(10 * self.screen_w / BASE_W))
        total_w = 2 * btn_w + gap
        start_x = actions.centerx - total_w // 2
        y = actions.centery - btn_h // 2
        self._buttons = [
            Button(pygame.Rect(start_x, y, btn_w, btn_h), "EXPORTER PDF",
                    Action.EXPORT_PDF, font=self._font,
                    variant="primary"),
            Button(pygame.Rect(start_x + btn_w + gap, y, btn_w, btn_h), "RETOUR MENU",
                    Action.BACK_MENU, font=self._font,
                    variant="quit"),
        ]

    def on_enter(self) -> None:
        self._font = load_font(scale_font_size(16, self.screen_h))
        self._font_small = load_font(scale_font_size(12, self.screen_h))
        self._build_buttons()

        if self.audio is not None:
            self.audio.play_music("race", loops=-1)

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
            width=self._zones.comparatif.width - 20,
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
                args=(
                    initial,
                    self.level_meta.name,
                    lane.progress_queue,
                    lane.cancel_event,
                    self._timeout_ms,
                ),
                daemon=True,
            )
            lane.thread.start()

    def handle_events(self) -> None:
        actions = poll_events(self._buttons, audio=self.audio)
        for action in actions:
            if action == Action.QUIT:
                self._cancel_all()
                self.manager.quit()
            elif action == Action.EXPORT_PDF:
                if self._all_done:
                    self._export_report()
            elif action == Action.BACK_MENU:
                self._cancel_all()
                # MODIFICATION : Arrêter les sons de la course et relancer la musique du menu
                if self.audio is not None:
                    self.audio.return_to_menu()
                from ui.scenes.menu import MenuScene
                self.manager.switch(MenuScene(
                    self.manager, audio=self.audio,
                    screen_w=self.screen_w, screen_h=self.screen_h,
                ))
                return

    def _cancel_all(self) -> None:
        for lane in self._lanes:
            lane.cancel_event.set()
        # Attendre brievement la prise en compte du cancel : evite de laisser
        # tourner des threads orphelins qui continueraient a pusher dans une
        # queue bientot abandonnee (retour menu -> relance d'une course =
        # threads qui cohabitent et artefacts visuels).
        for lane in self._lanes:
            if lane.thread is not None and lane.thread.is_alive():
                lane.thread.join(timeout=0.5)

    def update(self) -> None:
        for lane in self._lanes:
            for _ in range(MAX_PROGRESS_DRAIN_PER_FRAME):
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

                # Timeline : stocker (elapsed, nodes)
                if not progress.finished:
                    algo = progress.algo_name
                    if algo not in self._timelines:
                        self._timelines[algo] = []
                    self._timelines[algo].append((progress.elapsed_ms, progress.nodes_explored))

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

        zones = self._zones

        # Zone title : nom niveau centré
        title = f"Course : {self.level_meta.name}"
        title_surf = self._font.render(title, True, TEXT_COLOR)
        tx = zones.title.centerx - title_surf.get_width() // 2
        ty = zones.title.top + max(4, (zones.title.height - title_surf.get_height()) // 2)
        screen.blit(title_surf, (tx, ty))

        # Zone lanes : 3 sous-zones fixes par lane (header/board/stats)
        for i, lane in enumerate(self._lanes):
            lane_x = zones.lanes.left + i * self._lane_w

            if i > 0:
                pygame.draw.line(
                    screen, SEPARATOR_COLOR,
                    (lane_x, zones.lanes.top),
                    (lane_x, zones.lanes.bottom),
                )

            header_top = zones.lanes.top
            algo_name = lane.solver.name
            color = DONE_COLOR if lane.done else HEADER_COLOR
            name_surf = self._font.render(algo_name, True, color)
            screen.blit(name_surf, (
                lane_x + self._lane_w // 2 - name_surf.get_width() // 2,
                header_top + 4,
            ))
            if lane.done and lane.finish_order > 0:
                order_text = f"#{lane.finish_order}"
                order_surf = self._font.render(order_text, True, DONE_COLOR)
                screen.blit(order_surf, (
                    lane_x + self._lane_w - order_surf.get_width() - 8,
                    header_top + 4,
                ))

            board_top = zones.lanes.top + self._header_h
            if lane.result and lane.result.found and lane.result.steps:
                step_idx = min(lane.replay_step, len(lane.result.steps) - 1)
                state = lane.result.steps[step_idx].state_snapshot
            else:
                state = self._initial_state
            board_surf = self._renderers[i].render(state)
            bw, bh = board_surf.get_size()
            bx = lane_x + (self._lane_w - bw) // 2
            by = board_top + max(0, (self._board_h - bh) // 2)
            screen.blit(board_surf, (bx, by))

            stats_top = zones.lanes.top + self._header_h + self._board_h
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
            for idx, (text, color) in enumerate(lines):
                rendered = self._font_small.render(text, True, color)
                screen.blit(rendered, (lane_x + 8, stats_top + 4 + idx * line_h))

        # Zone comparatif : tableau live (affiché en permanence)
        comp_surf = self._metrics.render_comparison_live(self._lanes)
        cw, ch = comp_surf.get_size()
        cx = zones.comparatif.left + max(10, (zones.comparatif.width - cw) // 2)
        cy = zones.comparatif.top + max(5, (zones.comparatif.height - ch) // 2)
        screen.blit(comp_surf, (cx, cy))

        # Zone actions : boutons
        for btn in self._buttons:
            btn.draw(screen)

        # Toast de confirmation (par-dessus tout)
        self._draw_toast(screen)

    def _show_toast(self, text: str) -> None:
        """Affiche un message de confirmation temporaire."""
        self._toast_text = text
        self._toast_timer = pygame.time.get_ticks()

    def _draw_toast(self, screen: pygame.Surface) -> None:
        """Dessine le toast de confirmation s'il est actif."""
        if self._toast_text is None:
            return
        elapsed = pygame.time.get_ticks() - self._toast_timer
        if elapsed > self._toast_duration_ms:
            self._toast_text = None
            return

        assert self._font is not None
        alpha = 255
        fade_start = self._toast_duration_ms * 2 // 3
        if elapsed > fade_start:
            alpha = max(0, 255 - 255 * (elapsed - fade_start) // (self._toast_duration_ms - fade_start))

        pad_x, pad_y = 20, 10
        text_surf = self._font.render(self._toast_text, True, (255, 255, 255))
        tw, th = text_surf.get_size()
        box_w = tw + 2 * pad_x
        box_h = th + 2 * pad_y
        bx = (self.screen_w - box_w) // 2
        by = self.screen_h // 2 - box_h // 2

        toast_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        toast_surf.fill((46, 59, 29, alpha))  # INK with alpha
        pygame.draw.rect(toast_surf, (107, 142, 35, alpha), toast_surf.get_rect(), width=2, border_radius=8)
        text_surf.set_alpha(alpha)
        toast_surf.blit(text_surf, (pad_x, pad_y))
        screen.blit(toast_surf, (bx, by))

    def _export_report(self) -> None:
        """Exporte un rapport PDF de la course."""
        from ui.pdf_exporter import PDFExporter

        results = [lane.result for lane in self._lanes if lane.result is not None]
        if not results:
            self._show_toast("Aucun résultat à exporter")
            return

        level_safe = self.level_meta.name.replace('/', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"sokoban_race_{level_safe}_{timestamp}.pdf"
        project_root = Path(__file__).resolve().parent.parent.parent
        output_path = project_root / "doc" / output_filename

        exporter = PDFExporter(output_path)
        try:
            result_path = exporter.export(
                level_name=self.level_meta.name,
                initial_state=self._initial_state,
                results=results,
            )
            self._show_toast(f"PDF exporte : {result_path.name}")
            if self.audio is not None:
                self.audio.play_sfx("win")
        except Exception as e:
            self._show_toast(f"Erreur export : {e}")