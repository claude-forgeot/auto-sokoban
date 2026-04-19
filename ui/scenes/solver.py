"""
Scene de résolution automatique avec replay pas-à-pas.
Affiche les résultats de plusieurs algorithmes et permet de les comparer."""

from __future__ import annotations

import queue
import threading

import pygame

from game.level import LevelMeta, load_level
from solver.a_star import AStar
from game.board import Direction
from solver.base import DEFAULT_TIMEOUT_MS, Solver, SolverProgress, SolverResult
from solver.bfs import BFS
from solver.dfs import DFS
from ui.audio import AudioManager
from ui.fonts import load_font, load_mono, load_serif
from ui.layout import BASE_H, BASE_W, scale_font_size
from ui.input import Action, Button, poll_events
from ui.metrics_panel import MetricsPanel
from ui.renderer import Renderer
from ui.scenes.base import Scene, SceneManager

from ui.colors import (
    BG as BG_COLOR,
    INK as TEXT_COLOR,
    GOLD as STATUS_COLOR,
    SEPARATOR,
    PANEL,
    OLIVE,
    TERRACOTTA,
    TERRACOTTA_DARK,
)

REPLAY_SPEEDS = [
    ("0.25x", 1200),
    ("0.5x", 600),
    ("1x", 300),
    ("2x", 150),
    ("4x", 75),
]
DEFAULT_SPEED_IDX = 2  # 1x

TIMEOUT_OPTIONS_MS = [30_000, 60_000, 180_000]
DEFAULT_TIMEOUT_IDX = TIMEOUT_OPTIONS_MS.index(DEFAULT_TIMEOUT_MS)


class SolverScene(Scene):
    """Lance les solveurs, affiche replay pas-a-pas et tableau comparatif."""

    def __init__(
        self,
        manager: SceneManager,
        level_meta: LevelMeta,
        audio: AudioManager | None = None,
        screen_w: int = 800,
        screen_h: int = 600,
        tile_size: int = 48,
    ) -> None:
        super().__init__(manager)
        self.level_meta = level_meta
        # MODIFICATION : Ajout du paramétrage audio dans le constructeur
        # Cela permet à la scene solver d'accéder aux sons
        self.audio = audio
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.board = load_level(level_meta.path)
        self._initial_state = self.board.state
        self._base_tile_size = tile_size
        self._variant = hash(level_meta.name) % 3
        self.renderer = Renderer(
            tile_size=self._compute_tile_size(screen_w, screen_h),
            variant=self._variant,
        )
        self.metrics = MetricsPanel(
            width=max(350, int(350 * screen_w / BASE_W)),
            font_size=scale_font_size(16, screen_h),
        )

        self._solvers: list[Solver] = [AStar(), BFS(), DFS(max_depth=200)]
        self._results: list[SolverResult] = []
        self._current_solver_idx = 0
        self._current_result: SolverResult | None = None

        # Replay
        self._replay_step = 0
        self._replay_timer = 0
        self._replaying = False
        self._replay_done = False
        self._all_done = False
        self._speed_idx = DEFAULT_SPEED_IDX
        self._paused = False

        # Threading
        self._solver_thread: threading.Thread | None = None
        self._progress_queue: queue.Queue[SolverProgress] = queue.Queue()
        self._cancel_event = threading.Event()

        self._font: pygame.font.Font | None = None
        self._buttons: list[Button] = []
        self._stop_button: Button | None = None
        self._timeout_button: Button | None = None
        self._stopped = False
        self._timeout_idx = DEFAULT_TIMEOUT_IDX
        
        # MODIFICATION : Flag pour vérifier si le son de début a été joué
        self._game_start_sound_played = False

        # Heatmap
        self._show_heatmap = False
        self._visit_counts: dict[tuple[int, int], int] = {}

        # Timeline progression (algo_name -> list[(elapsed_ms, nodes)])
        self._timelines: dict[str, list[tuple[float, int]]] = {}

    def _compute_tile_size(self, screen_w: int, screen_h: int) -> int:
        panel_w = 370
        header_h = 40
        available_w = screen_w - panel_w - 20
        available_h = screen_h - header_h - 60
        cols = self._initial_state.width
        rows = self._initial_state.height
        adaptive_tile = min(
            self._base_tile_size,
            available_w // max(cols, 1),
            available_h // max(rows, 1),
        )
        return max(16, adaptive_tile)

    def _build_layout(self) -> None:
        assert self._font is not None
        sx = self.screen_w / BASE_W
        sy = self.screen_h / BASE_H
        btn_w = max(140, int(140 * sx))
        btn_h = max(35, int(35 * sy))
        spacing = max(45, int(45 * sy))
        x = self.screen_w - btn_w - int(20 * sx)
        y_base = self.screen_h - max(200, int(200 * sy))
        self._buttons = [
            Button(pygame.Rect(x, y_base, btn_w, btn_h), "REJOUER", Action.RESET, font=self._font,
                    variant="primary"),
            Button(pygame.Rect(x, y_base + spacing, btn_w, btn_h), "ALGO SUIVANT", Action.SOLVE,
                   font=self._font, variant="solve"),
            Button(pygame.Rect(x, y_base + spacing * 2, btn_w, btn_h), "HEATMAP [H]", Action.HEATMAP,
                   font=self._font, variant="rank"),
            Button(pygame.Rect(x, y_base + spacing * 3 + int(10 * sy), btn_w, btn_h), "RETOUR MENU",
                   Action.BACK_MENU, font=self._font, variant="quit"),
        ]
        self._stop_button = Button(
            pygame.Rect(x, y_base - spacing, btn_w, btn_h),
            "STOP",
            Action.STOP_SOLVER,
            font=self._font,
            color=TERRACOTTA,
            shadow_color=TERRACOTTA_DARK,
            text_color=(255, 255, 255),
        )
        self._timeout_button = Button(
            pygame.Rect(x, y_base - spacing * 2, btn_w, btn_h),
            self._timeout_label(),
            Action.CYCLE_TIMEOUT,
            font=self._font,
            variant="ghost",
        )

    def _timeout_label(self) -> str:
        seconds = TIMEOUT_OPTIONS_MS[self._timeout_idx] // 1000
        return f"TIMEOUT {seconds}s [T]"

    def on_enter(self) -> None:
        """Initialise la scene de résolution automatique.

        Cette méthode est appelée lorsque l'utilisateur accède au mode de résolution automatique.
        C'est le bon moment pour jouer le son de début et lancer l'algorithme de résolution.
        """
        self._font = load_font(scale_font_size(18, self.screen_h))
        self._build_layout()

        if self.audio is not None:
            self.audio.play_music("game_start", loops=0)

        self._run_current_solver()

    def on_resize(self, new_w: int, new_h: int) -> None:
        self.screen_w = new_w
        self.screen_h = new_h
        self.renderer = Renderer(
            tile_size=self._compute_tile_size(new_w, new_h),
            variant=self._variant,
        )
        if self._font is not None:
            self._build_layout()

    def _run_current_solver(self) -> None:
        """Lance le solveur courant dans un thread separe."""
        if self._current_solver_idx >= len(self._solvers):
            self._all_done = True
            return

        if self._solver_thread is not None and self._solver_thread.is_alive():
            return

        solver = self._solvers[self._current_solver_idx]
        initial = load_level(self.level_meta.path).state

        # Reset queue, event et heatmap
        self._progress_queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._visit_counts = {}
        self._stopped = False

        timeout_ms = TIMEOUT_OPTIONS_MS[self._timeout_idx]
        self.metrics.set_timeout(timeout_ms)
        self._solver_thread = threading.Thread(
            target=solver.solve_async,
            args=(initial, self.level_meta.name, self._progress_queue, self._cancel_event, timeout_ms),
            daemon=True,
        )
        self._solver_thread.start()

    def handle_events(self) -> None:
        """Traite les entrées utilisateur."""
        solver_running = self._solver_thread is not None and self._solver_thread.is_alive()
        buttons = list(self._buttons)
        if solver_running and self._stop_button is not None:
            buttons.append(self._stop_button)
        if not solver_running and self._timeout_button is not None:
            buttons.append(self._timeout_button)
        actions = poll_events(buttons)
        for action in actions:
            if action == Action.QUIT:
                self.manager.quit()
            elif action == Action.STOP_SOLVER:
                if solver_running:
                    self._cancel_event.set()
                    self._stopped = True
            elif action == Action.CYCLE_TIMEOUT:
                if not solver_running:
                    self._timeout_idx = (self._timeout_idx + 1) % len(TIMEOUT_OPTIONS_MS)
                    if self._timeout_button is not None:
                        self._timeout_button.label = self._timeout_label()
            elif action == Action.BACK_MENU:
                self._cancel_event.set()
                if self.audio is not None:
                    self.audio.return_to_menu()  # Assurer la transition audio vers le menu
                from ui.scenes.menu import MenuScene
                menu = MenuScene(
                    self.manager,
                    audio=self.audio,
                    screen_w=self.screen_w,
                    screen_h=self.screen_h,
                )
                self.manager.switch(menu)
                return
            elif action == Action.RESET:
                # Rejouer le replay du solveur courant
                if self._current_result and self._current_result.found:
                    self._replay_step = 0
                    self._replay_timer = pygame.time.get_ticks()
                    self._replaying = True
                    self._replay_done = False
            elif action == Action.SOLVE:
                # Passer au solveur suivant
                if solver_running:
                    continue
                if self._replay_done or not self._replaying:
                    self._current_solver_idx += 1
                    self._run_current_solver()
            elif action == Action.HEATMAP:
                self._show_heatmap = not self._show_heatmap
            elif action == Action.SPEED_UP:
                if self._speed_idx < len(REPLAY_SPEEDS) - 1:
                    self._speed_idx += 1
            elif action == Action.SPEED_DOWN:
                if self._speed_idx > 0:
                    self._speed_idx -= 1
            elif action == Action.PAUSE:
                self._paused = not self._paused
            elif action == Action.MOVE_LEFT and self._paused and self._replaying:
                if self._replay_step > 0:
                    self._replay_step -= 1
            elif action == Action.MOVE_RIGHT and self._paused and self._replaying:
                if self._current_result and self._replay_step < len(self._current_result.steps) - 1:
                    self._replay_step += 1

    def update(self) -> None:
        """Met à jour l'état du replay automatique."""
        # Poller les messages de progression du solveur
        while not self._progress_queue.empty():
            try:
                progress = self._progress_queue.get_nowait()
            except queue.Empty:
                break

            if progress.visit_counts:
                self._visit_counts = progress.visit_counts

            # Timeline : stocker (elapsed, nodes)
            algo = progress.algo_name
            if algo not in self._timelines:
                self._timelines[algo] = []
            self._timelines[algo].append((progress.elapsed_ms, progress.nodes_explored))

            if progress.finished and progress.result is not None:
                self._current_result = progress.result
                self._results.append(progress.result)
                self.metrics.update(progress.result)
                self.metrics.clear_progress()
                if progress.result.visit_counts:
                    self._visit_counts = progress.result.visit_counts

                # Demarrer le replay
                self._replay_step = 0
                self._replay_timer = pygame.time.get_ticks()
                self._replaying = progress.result.found and len(progress.result.steps) > 0
                self._replay_done = not self._replaying
                self._solver_thread = None
            else:
                self.metrics.update_progress(progress)

        # Replay pas-a-pas
        if not self._replaying or self._paused:
            return

        delay = REPLAY_SPEEDS[self._speed_idx][1]
        now = pygame.time.get_ticks()
        if now - self._replay_timer >= delay:
            self._replay_timer = now
            self._replay_step += 1
            
            # MODIFICATION : Jouer le son lors de chaque pas du replay
            # On vérifie si une caisse a ete poussée au pas actuel
            if self._current_result and self._replay_step <= len(self._current_result.steps):
                # Récuperer l'étape actuelle et l'étape précédente pour comparer
                current_step_idx = min(self._replay_step - 1, len(self._current_result.steps) - 1)
                if current_step_idx > 0:
                    prev_step = self._current_result.steps[current_step_idx - 1]
                    curr_step = self._current_result.steps[current_step_idx]
                    # Si les positions des caisses ont change, c'est une poussee
                    if prev_step.state_snapshot.boxes != curr_step.state_snapshot.boxes:
                        if self.audio is not None:
                            self.audio.play_bottle_clank()
                    else:
                        # Sinon c'est juste un mouvement
                        if self.audio is not None:
                            self.audio.play_sfx("move")
            
            # Vérification de fin de replay
            if self._current_result and self._replay_step >= len(self._current_result.steps):
                self._replaying = False
                self._replay_done = True

    def draw(self, screen: pygame.Surface) -> None:
        """Dessine la scene de résolution automatique."""
        screen.fill(BG_COLOR)
        assert self._font is not None

        # Titre
        title = f"Résolution : {self.level_meta.name}"
        title_surf = self._font.render(title, True, TEXT_COLOR)
        screen.blit(title_surf, (20, 10))

        # Etat du plateau (replay)
        facing_left = False
        if self._current_result and self._current_result.found and self._current_result.steps:
            step_idx = min(self._replay_step, len(self._current_result.steps) - 1)
            state = self._current_result.steps[step_idx].state_snapshot
            d = self._current_result.steps[step_idx].direction
            if d == Direction.LEFT:
                facing_left = True
        else:
            state = self._initial_state

        board_surface = self.renderer.render(state, facing_left=facing_left)
        if self._show_heatmap and self._visit_counts:
            heatmap = self.renderer.render_heatmap_overlay(state, self._visit_counts)
            board_surface.blit(heatmap, (0, 0))
        if self._replaying or self._replay_done:
            deadlock_overlay = self.renderer.render_deadlock_overlay(state)
            board_surface.blit(deadlock_overlay, (0, 0))
        bw, bh = board_surface.get_size()
        panel_w = 370
        available_w = self.screen_w - panel_w
        gx = (available_w - bw) // 2
        gy = 40 + (self.screen_h - 40 - bh) // 2
        screen.blit(board_surface, (max(10, gx), max(40, gy)))

        # Panneau metriques (droite)
        solver_running = self._solver_thread is not None and self._solver_thread.is_alive()
        if self._all_done:
            metrics_surf = self.metrics.render_comparison(self._results)
            screen.blit(metrics_surf, (self.screen_w - panel_w, 40))
            # La timeline doit eviter la pile de boutons droite. On borne sa
            # largeur jusqu'au btn_left et sa hauteur jusqu'au btn_top le plus
            # haut (TIMEOUT depasse la pile REJOUER...). Fix partiel : avec le
            # layout boutons actuel #230, la timeline reste etroite -- la refonte
            # globale est suivie dans #230.
            tl_x = self.screen_w - panel_w
            tl_y = 40 + metrics_surf.get_height() + 6
            right_buttons = list(self._buttons)
            if self._timeout_button is not None:
                right_buttons.append(self._timeout_button)
            btn_left = min((b.rect.left for b in right_buttons), default=self.screen_w)
            btn_top = min((b.rect.top for b in right_buttons), default=self.screen_h)
            tl_w = max(180, btn_left - tl_x - 10)
            tl_h = max(80, btn_top - tl_y - 10)
            timeline_surf = self.metrics.render_timeline(
                self._timelines, width=tl_w, height=tl_h,
            )
            screen.blit(timeline_surf, (tl_x, tl_y))
        elif solver_running:
            metrics_surf = self.metrics.render_progress()
            screen.blit(metrics_surf, (self.screen_w - panel_w, 40))
        else:
            metrics_surf = self.metrics.render()
            screen.blit(metrics_surf, (self.screen_w - panel_w, 40))

        # Status
        if self._solver_thread is not None and self._solver_thread.is_alive():
            algo = self._solvers[self._current_solver_idx].name
            if self._stopped:
                status = f"[{algo}] Arrêt en cours..."
            else:
                status = f"[{algo}] Résolution en cours..."
            status_surf = self._font.render(status, True, STATUS_COLOR)
            line_h = self._font.get_linesize()
            screen.blit(status_surf, (20, self.screen_h - line_h * 2 - 8))
        elif self._current_result:
            algo = self._current_result.algo_name
            reason = self._current_result.stop_reason
            if self._replaying:
                status = f"[{algo}] Replay : pas {self._replay_step + 1}/{len(self._current_result.steps)}"
            elif self._all_done:
                status = "Tous les algorithmes terminés - Comparaison finale"
            elif reason == "user_cancelled":
                status = f"[{algo}] Résolution stoppée"
            elif reason == "timeout":
                timeout_s = TIMEOUT_OPTIONS_MS[self._timeout_idx] // 1000
                status = f"[{algo}] Timeout atteint ({timeout_s}s) - Pas de solution"
            elif self._replay_done:
                status = f"[{algo}] Terminé - Appuyez sur ALGO SUIVANT"
            elif not self._current_result.found:
                status = f"[{algo}] Pas de solution trouvée"
            else:
                status = f"[{algo}] En cours..."
            status_surf = self._font.render(status, True, STATUS_COLOR)
            line_h = self._font.get_linesize()
            screen.blit(status_surf, (20, self.screen_h - line_h * 2 - 8))

        # Indicateur vitesse / pause : pertinent uniquement pendant le replay.
        if self._replaying:
            speed_label = REPLAY_SPEEDS[self._speed_idx][0]
            if self._paused:
                speed_text = f"PAUSE | {speed_label} | [-/+] vitesse | [</>] pas"
            else:
                speed_text = f"{speed_label} | [-/+] vitesse | [ESPACE] pause"
            speed_surf = self._font.render(speed_text, True, STATUS_COLOR)
            screen.blit(speed_surf, (20, self.screen_h - self._font.get_linesize() - 4))

        # Boutons
        for btn in self._buttons:
            btn.draw(screen)
        if solver_running and self._stop_button is not None:
            self._stop_button.draw(screen)
        if not solver_running and self._timeout_button is not None:
            self._timeout_button.draw(screen)