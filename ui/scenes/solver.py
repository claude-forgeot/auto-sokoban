"""
Scene de résolution automatique avec replay pas-à-pas.
Affiche les résultats de plusieurs algorithmes et permet de les comparer."""

from __future__ import annotations

import queue
import threading

import pygame

from game.level import LevelMeta, load_level
from solver.a_star import AStar
from solver.base import Solver, SolverProgress, SolverResult
from solver.bfs import BFS
from solver.dfs import DFS
from ui.audio import AudioManager
from ui.fonts import load_font
from ui.input import Action, Button, poll_events
from ui.metrics_panel import MetricsPanel
from ui.renderer import Renderer
from ui.scenes.base import Scene, SceneManager

BG_COLOR = (25, 25, 35)
TEXT_COLOR = (220, 220, 220)
STATUS_COLOR = (255, 220, 80)

REPLAY_DELAY_MS = 300  # delai entre chaque pas du replay


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
        panel_w = 370
        header_h = 40
        available_w = screen_w - panel_w - 20
        available_h = screen_h - header_h - 60
        cols = self._initial_state.width
        rows = self._initial_state.height
        adaptive_tile = min(tile_size, available_w // max(cols, 1), available_h // max(rows, 1))
        variant = hash(level_meta.name) % 3
        self.renderer = Renderer(tile_size=max(16, adaptive_tile), variant=variant)
        self.metrics = MetricsPanel(width=350)

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

        # Threading
        self._solver_thread: threading.Thread | None = None
        self._progress_queue: queue.Queue[SolverProgress] = queue.Queue()
        self._cancel_event = threading.Event()

        self._font: pygame.font.Font | None = None
        self._buttons: list[Button] = []
        
        # MODIFICATION : Flag pour vérifier si le son de début a été joué
        self._game_start_sound_played = False

    def on_enter(self) -> None:
        """Initialise la scene de résolution automatique.
        
        Cette méthode est appelée lorsque l'utilisateur accède au mode de résolution automatique. C'est le bon moment pour jouer le son de début et lancer l'algorithme de résolution.
        """
        self._font = load_font(18)

        btn_w, btn_h = 140, 35
        x = self.screen_w - btn_w - 20
        y_base = self.screen_h - 200
        spacing = 45

        self._buttons = [
            Button(pygame.Rect(x, y_base, btn_w, btn_h), "REJOUER", Action.RESET, font=self._font,
                    color=(40, 100, 40), hover_color=(60, 140, 60)),
            Button(pygame.Rect(x, y_base + spacing, btn_w, btn_h), "ALGO SUIVANT", Action.SOLVE,
                    font=self._font, color=(40, 40, 100), hover_color=(60, 60, 140)),
            Button(pygame.Rect(x, y_base + spacing * 2 + 10, btn_w, btn_h), "RETOUR MENU",
                    Action.BACK_MENU, font=self._font, color=(100, 40, 40), hover_color=(140, 60, 60)),
        ]
        
        # MODIFICATION : Jouer le son de début lorsqu'on entre en mode résolution
        if self.audio is not None:
            self.audio.play_game_start()

        self._run_current_solver()

    def _run_current_solver(self) -> None:
        """Lance le solveur courant dans un thread separe."""
        if self._current_solver_idx >= len(self._solvers):
            self._all_done = True
            return

        solver = self._solvers[self._current_solver_idx]
        initial = load_level(self.level_meta.path).state

        # Reset queue et event
        self._progress_queue = queue.Queue()
        self._cancel_event = threading.Event()

        self._solver_thread = threading.Thread(
            target=solver.solve_async,
            args=(initial, self.level_meta.name, self._progress_queue, self._cancel_event),
            daemon=True,
        )
        self._solver_thread.start()

    def handle_events(self) -> None:
        """Traite les entrées utilisateur."""
        actions = poll_events(self._buttons)
        for action in actions:
            if action == Action.QUIT:
                self.manager.quit()
            elif action == Action.BACK_MENU:
                self._cancel_event.set()
                from ui.scenes.menu import MenuScene
                menu = MenuScene(
                    self.manager,
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
                if self._replay_done or not self._replaying:
                    self._current_solver_idx += 1
                    self._run_current_solver()

    def update(self) -> None:
        """Met à jour l'état du replay automatique."""
        # Poller les messages de progression du solveur
        while not self._progress_queue.empty():
            try:
                progress = self._progress_queue.get_nowait()
            except queue.Empty:
                break

            if progress.finished and progress.result is not None:
                self._current_result = progress.result
                self._results.append(progress.result)
                self.metrics.update(progress.result)

                # Demarrer le replay
                self._replay_step = 0
                self._replay_timer = pygame.time.get_ticks()
                self._replaying = progress.result.found and len(progress.result.steps) > 0
                self._replay_done = not self._replaying
                self._solver_thread = None

        # Replay pas-à-pas de la solution
        if not self._replaying:
            return

        now = pygame.time.get_ticks()
        if now - self._replay_timer >= REPLAY_DELAY_MS:
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
        if self._current_result and self._current_result.found and self._current_result.steps:
            step_idx = min(self._replay_step, len(self._current_result.steps) - 1)
            state = self._current_result.steps[step_idx].state_snapshot
        else:
            state = self._initial_state

        board_surface = self.renderer.render(state)
        bw, bh = board_surface.get_size()
        panel_w = 370
        available_w = self.screen_w - panel_w
        gx = (available_w - bw) // 2
        gy = 40 + (self.screen_h - 40 - bh) // 2
        screen.blit(board_surface, (max(10, gx), max(40, gy)))

        # Panneau metriques (droite)
        if self._all_done:
            metrics_surf = self.metrics.render_comparison(self._results)
        else:
            metrics_surf = self.metrics.render()
        screen.blit(metrics_surf, (self.screen_w - panel_w, 40))

        # Status
        if self._solver_thread is not None and self._solver_thread.is_alive():
            algo = self._solvers[self._current_solver_idx].name
            status = f"[{algo}] Résolution en cours..."
            status_surf = self._font.render(status, True, STATUS_COLOR)
            screen.blit(status_surf, (20, self.screen_h - 40))
        elif self._current_result:
            algo = self._current_result.algo_name
            if self._replaying:
                status = f"[{algo}] Replay : pas {self._replay_step + 1}/{len(self._current_result.steps)}"
            elif self._all_done:
                status = "Tous les algorithmes terminés - Comparaison finale"
            elif self._replay_done:
                status = f"[{algo}] Terminé - Appuyez sur ALGO SUIVANT"
            elif not self._current_result.found:
                status = f"[{algo}] Pas de solution trouvée"
            else:
                status = f"[{algo}] En cours..."
            status_surf = self._font.render(status, True, STATUS_COLOR)
            screen.blit(status_surf, (20, self.screen_h - 40))

        # Boutons
        for btn in self._buttons:
            btn.draw(screen)