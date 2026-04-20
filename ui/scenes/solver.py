"""
Scene de résolution automatique avec replay pas-à-pas.
Affiche les résultats de plusieurs algorithmes et permet de les comparer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
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
from ui.layout import BASE_H, BASE_W, SolverZones, compute_solver_zones, scale_font_size
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

# Meme garde-fou que RaceScene : borner le drain de la queue par frame
# sinon le thread principal ne rend jamais la main a pygame.event.get().
MAX_PROGRESS_DRAIN_PER_FRAME = 200
# Limite souple des points de timeline par algo : decimation 1 sur 2 au-dela
# pour conserver la courbe complete sans saturer memoire et rendu.
MAX_TIMELINE_POINTS = 500


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
        self._zones: SolverZones = compute_solver_zones(screen_w, screen_h)

        self.board = load_level(level_meta.path)
        self._initial_state = self.board.state
        self._base_tile_size = tile_size
        self._variant = hash(level_meta.name) % 3
        self.renderer = Renderer(
            tile_size=self._compute_tile_size(screen_w, screen_h),
            variant=self._variant,
        )
        self.metrics = MetricsPanel(
            width=self._zones.metrics.width - 20,
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

        # Toast confirmation
        self._toast_text: str | None = None
        self._toast_timer: int = 0
        self._toast_duration_ms: int = 3000
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
        zones = compute_solver_zones(screen_w, screen_h)
        available_w = zones.board.width - 20
        available_h = zones.board.height - 20
        cols = self._initial_state.width
        rows = self._initial_state.height
        adaptive_tile = min(
            self._base_tile_size * 2,  # x2 : permet de grossir à HD
            available_w // max(cols, 1),
            available_h // max(rows, 1),
        )
        return max(16, adaptive_tile)

    def _build_layout(self) -> None:
        assert self._font is not None
        # Recalcul des zones au cas où on arrive ici après un resize.
        self._zones = compute_solver_zones(self.screen_w, self.screen_h)
        a = self._zones.actions
        sy = self.screen_h / BASE_H
        btn_h = max(35, int(35 * sy))
        btn_spacing = max(6, int(6 * sy))
        slot_h = btn_h + btn_spacing
        btn_x = a.left + 10
        btn_w = a.width - 20

        def _slot_y(idx: int) -> int:
            # 6 slots empilés : [0]=STOP/TIMEOUT (contextuel), [1..5]=fixes
            return a.top + 10 + idx * slot_h

        self._buttons = [
            Button(pygame.Rect(btn_x, _slot_y(1), btn_w, btn_h), "REJOUER",
                Action.RESET, font=self._font, variant="primary"),
            Button(pygame.Rect(btn_x, _slot_y(2), btn_w, btn_h), "ALGO SUIVANT",
                Action.SOLVE, font=self._font, variant="solve"),
            Button(pygame.Rect(btn_x, _slot_y(3), btn_w, btn_h), "HEATMAP [H]",
                Action.HEATMAP, font=self._font, variant="rank"),
            Button(pygame.Rect(btn_x, _slot_y(4), btn_w, btn_h), "EXPORTER PDF",
                Action.EXPORT_PDF, font=self._font, variant="primary"),
            Button(pygame.Rect(btn_x, _slot_y(5), btn_w, btn_h), "RETOUR MENU",
                Action.BACK_MENU, font=self._font, variant="quit"),
        ]
        self._stop_button = Button(
            pygame.Rect(btn_x, _slot_y(0), btn_w, btn_h),
            "STOP",
            Action.STOP_SOLVER,
            font=self._font,
            color=TERRACOTTA,
            shadow_color=TERRACOTTA_DARK,
            text_color=(255, 255, 255),
        )
        self._timeout_button = Button(
            pygame.Rect(btn_x, _slot_y(0), btn_w, btn_h),
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
                    if self.audio is not None:
                        self.audio.play_sfx("move")  # Son de mouvement pour le début du replay
            elif action == Action.SOLVE:
                # Passer au solveur suivant
                if solver_running:
                    return
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
            elif action == Action.EXPORT_PDF:
                if self._all_done:
                    self.export_report()

    def update(self) -> None:
        """Met à jour l'état du replay automatique."""
        # Poller les messages de progression du solveur (drain borne : meme
        # raisonnement que RaceScene, evite le freeze de la fenetre quand
        # le thread solveur inonde la queue plus vite qu'on ne draine).
        for _ in range(MAX_PROGRESS_DRAIN_PER_FRAME):
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
            if len(self._timelines[algo]) > MAX_TIMELINE_POINTS:
                # Decimation 1/2 : conserve la courbe complete (debut + fin)
                # au prix d'une resolution temporelle divisee par 2.
                self._timelines[algo] = self._timelines[algo][::2]

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
        bz = self._zones.board
        gx = bz.left + (bz.width - bw) // 2
        gy = bz.top + (bz.height - bh) // 2
        screen.blit(board_surface, (max(bz.left + 10, gx), max(bz.top, gy)))

        # Panneau métriques (zone droite haute des zones nommées)
        solver_running = self._solver_thread is not None and self._solver_thread.is_alive()
        m = self._zones.metrics
        if self._all_done:
            metrics_surf = self.metrics.render_comparison(self._results)
            screen.blit(metrics_surf, (m.left + 10, m.top + 10))
            comp_h = metrics_surf.get_height()
            # Timeline remplit la hauteur restante dans zones.metrics
            # (zones disjointes => jamais sous les boutons actions).
            # Skip si espace < 40px : a MIN_H=480 le tableau comparatif
            # remplit deja toute la zone, la timeline serait illisible.
            tl_h_avail = m.height - 10 - comp_h - 6 - 10
            if tl_h_avail >= 40:
                timeline_surf = self.metrics.render_timeline(
                    self._timelines, width=m.width - 20, height=tl_h_avail,
                )
                screen.blit(timeline_surf, (m.left + 10, m.top + 10 + comp_h + 6))
        elif solver_running:
            metrics_surf = self.metrics.render_progress()
            screen.blit(metrics_surf, (m.left + 10, m.top + 10))
        else:
            metrics_surf = self.metrics.render()
            screen.blit(metrics_surf, (m.left + 10, m.top + 10))

        # Status + speed : regroupes dans un bandeau footer PANEL en bas du plateau
        # pour les relier visuellement au reste de l'UI (audit 2026-04-19 #235).
        footer_lines: list[str] = []
        if self._solver_thread is not None and self._solver_thread.is_alive():
            algo = self._solvers[self._current_solver_idx].name
            if self._stopped:
                footer_lines.append(f"[{algo}] Arrêt en cours...")
            else:
                footer_lines.append(f"[{algo}] Résolution en cours...")
        elif self._current_result:
            algo = self._current_result.algo_name
            reason = self._current_result.stop_reason
            if self._replaying:
                footer_lines.append(
                    f"[{algo}] Replay : pas {self._replay_step + 1}/{len(self._current_result.steps)}"
                )
            elif self._all_done:
                footer_lines.append("Tous les algorithmes terminés - Comparaison finale")
            elif reason == "user_cancelled":
                footer_lines.append(f"[{algo}] Résolution stoppée")
            elif reason == "timeout":
                timeout_s = TIMEOUT_OPTIONS_MS[self._timeout_idx] // 1000
                footer_lines.append(f"[{algo}] Timeout atteint ({timeout_s}s) - Pas de solution")
            elif self._replay_done:
                footer_lines.append(f"[{algo}] Terminé - Appuyez sur ALGO SUIVANT")
            elif not self._current_result.found:
                footer_lines.append(f"[{algo}] Pas de solution trouvée")
            else:
                footer_lines.append(f"[{algo}] En cours...")

        if self._replaying:
            speed_label = REPLAY_SPEEDS[self._speed_idx][0]
            if self._paused:
                footer_lines.append(f"PAUSE | {speed_label} | [-/+] vitesse | [</>] pas")
            else:
                footer_lines.append(f"{speed_label} | [-/+] vitesse | [ESPACE] pause")

        if footer_lines:
            line_h = self._font.get_linesize()
            pad = 8
            bandeau_h = line_h * len(footer_lines) + 2 * pad
            bandeau_rect = pygame.Rect(
                0, self.screen_h - bandeau_h, self._zones.board.width, bandeau_h
            )
            pygame.draw.rect(screen, PANEL, bandeau_rect)
            pygame.draw.line(
                screen, SEPARATOR,
                (bandeau_rect.left, bandeau_rect.top),
                (bandeau_rect.right, bandeau_rect.top),
                width=1,
            )
            y = bandeau_rect.top + pad
            for text in footer_lines:
                surf = self._font.render(text, True, STATUS_COLOR)
                # Status final "comparaison finale" centre pour equilibrer le
                # bandeau quand il ne contient qu'une ligne isolee (audit #236).
                if self._all_done and text.startswith("Tous les algorithmes"):
                    x = bandeau_rect.centerx - surf.get_width() // 2
                else:
                    x = 20
                screen.blit(surf, (x, y))
                y += line_h

        # Boutons
        for btn in self._buttons:
            btn.draw(screen)
        if solver_running and self._stop_button is not None:
            self._stop_button.draw(screen)
        if not solver_running and self._timeout_button is not None:
            self._timeout_button.draw(screen)

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
        # Fade out dans le dernier tiers
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
        pygame.draw.rect(toast_surf, (107, 142, 35, alpha), toast_surf.get_rect(), width=2, border_radius=8)  # SAGE border
        text_surf.set_alpha(alpha)
        toast_surf.blit(text_surf, (pad_x, pad_y))
        screen.blit(toast_surf, (bx, by))

    def export_report(self) -> None:
        """Exporte un rapport PDF détaillé des résultats."""
        from ui.pdf_exporter import PDFExporter
        
        if not self._results:
            self._show_toast("Aucun résultat à exporter")
            return
        
        # Créer le nom du fichier dans le dossier doc/
        level_safe = self.level_meta.name.replace('/', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"sokoban_report_{level_safe}_{timestamp}.pdf"
        project_root = Path(__file__).resolve().parent.parent.parent
        output_path = project_root / "doc" / output_filename
        
        exporter = PDFExporter(output_path)
        try:
            result_path = exporter.export(
                level_name=self.level_meta.name,
                initial_state=self._initial_state,
                results=self._results,
            )
            self._show_toast(f"PDF exporte : {result_path.name}")
            if self.audio is not None:
                self.audio.play_sfx("win")
        except Exception as e:
            self._show_toast(f"Erreur export : {e}")