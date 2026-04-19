"""Scene de jeu humain (gameplay interactif)."""

from __future__ import annotations

import math
import time

import pygame

from game.board import Direction, detect_freeze_deadlocks, is_lost
from game.db import save_score
from game.level import LevelMeta, load_level
from ui.audio import AudioManager
from ui.input import Action, Button, poll_events
from ui.fonts import load_font, load_mono, load_serif
from ui.layout import scale_font_size
from ui.renderer import Renderer
from ui.scenes.base import Scene, SceneManager

from ui.colors import (
    BG as BG_COLOR,
    INK as HUD_COLOR,
    SAGE as WIN_COLOR,
    SAGE_DARK as LABEL_COLOR,
    PANEL as HUD_BG,
    OLIVE as HUD_BORDER,
    BG as INPUT_COLOR,
)

_ACTION_TO_DIR = {
    Action.MOVE_UP: Direction.UP,
    Action.MOVE_DOWN: Direction.DOWN,
    Action.MOVE_LEFT: Direction.LEFT,
    Action.MOVE_RIGHT: Direction.RIGHT,
}


class GameScene(Scene):
    """Scene de jeu : grille, HUD, controles."""

    def __init__(
        self,
        manager: SceneManager,
        level_meta: LevelMeta,
        audio: AudioManager,
        screen_w: int = 800,
        screen_h: int = 600,
        tile_size: int = 64,
    ) -> None:
        super().__init__(manager)
        self.level_meta = level_meta
        self.audio = audio
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.board = load_level(level_meta.path)
        self._base_tile_size = tile_size
        self._variant = hash(level_meta.name) % 3
        self.renderer = Renderer(
            tile_size=self._compute_tile_size(screen_w, screen_h),
            variant=self._variant,
        )
        self.move_count = 0
        self.start_time = 0.0
        self.won = False

        self._font: pygame.font.Font | None = None
        self._font_label: pygame.font.Font | None = None
        self._buttons: list[Button] = []
        self._entering_name = False
        self._player_name = ""
        self._score_saved = False
        self._win_elapsed = 0.0
        self._confirm_solve = False
        self._facing_left = False
        self._invalid_move_shake_start: int = 0

        # MODIFICATION : Flag pour vérifier si le son de début a été joué
        # Cela permet de lancer le son game_start une seule fois au démarrage
        self._game_start_sound_played = False

    def _compute_tile_size(self, screen_w: int, screen_h: int) -> int:
        hud_h = 50
        actions_h = max(50, int(60 * screen_h / 600))
        available_w = screen_w - 40
        available_h = screen_h - hud_h - actions_h - 20
        cols = self.board.state.width
        rows = self.board.state.height
        adaptive_tile = min(
            self._base_tile_size,
            available_w // max(cols, 1),
            available_h // max(rows, 1),
        )
        return max(16, adaptive_tile)

    def _build_layout(self) -> None:
        assert self._font is not None
        sy = self.screen_h / 600
        bar_h = max(50, int(60 * sy))
        btn_h = max(35, int(35 * sy))
        margin_x = 10
        gap = 8
        n_btn = 5
        btn_w = max(90, (self.screen_w - 2 * margin_x - (n_btn - 1) * gap) // n_btn)
        bar_top = self.screen_h - bar_h
        y = bar_top + (bar_h - btn_h) // 2

        def _bx(i: int) -> int:
            return margin_x + i * (btn_w + gap)

        self._buttons = [
            Button(pygame.Rect(_bx(0), y, btn_w, btn_h), "ANNULER", Action.UNDO, font=self._font, variant="ghost"),
            Button(pygame.Rect(_bx(1), y, btn_w, btn_h), "RÉINIT.", Action.RESET, font=self._font, variant="ghost"),
            Button(pygame.Rect(_bx(2), y, btn_w, btn_h), "RÉSOUDRE", Action.SOLVE, font=self._font, variant="solve"),
            Button(pygame.Rect(_bx(3), y, btn_w, btn_h), "ABANDONNER", Action.ABANDON, font=self._font, variant="quit"),
            Button(pygame.Rect(_bx(4), y, btn_w, btn_h), "QUITTER", Action.BACK_MENU, font=self._font, variant="quit"),
        ]

    def on_enter(self) -> None:
        """Initialise la scene lorsqu'elle devient active.

        Cette méthode est appelée au moment où le joueur accède à un nouveau niveau.
        C'est le bon moment pour jouer le son de début de niveau.
        """
        pygame.font.init()
        self._font = load_mono(scale_font_size(18, self.screen_h))
        self._font_label = load_serif(scale_font_size(14, self.screen_h), weight="bold")
        self._build_layout()
        self.start_time = time.time()
        
        if not self._game_start_sound_played:
            self.audio.play_music("game_start", loops=0)
            self._game_start_sound_played = True

    def on_resize(self, new_w: int, new_h: int) -> None:
        self.screen_w = new_w
        self.screen_h = new_h
        self.renderer = Renderer(
            tile_size=self._compute_tile_size(new_w, new_h),
            variant=self._variant,
        )
        self._build_layout()

    def handle_events(self) -> None:
        """Traite les entrées utilisateur (clavier, souris, boutons)."""
        if self._entering_name:
            self._handle_name_input()
            return

        if self._confirm_solve:
            self._handle_solve_confirm()
            return

        actions = poll_events(self._buttons, audio=self.audio)
        for action in actions:
            if action == Action.QUIT:
                self.manager.quit()
            elif action == Action.BACK_MENU:
                self.audio.return_to_menu()  # Assurer la transition audio vers le menu
                from ui.scenes.menu import MenuScene
                menu = MenuScene(
                    self.manager, audio=self.audio,
                    screen_w=self.screen_w, screen_h=self.screen_h,
                )
                self.manager.switch(menu)
                return
            elif action in _ACTION_TO_DIR and not self.won:
                direction = _ACTION_TO_DIR[action]
                if not self.board.move(direction):
                    self._invalid_move_shake_start = pygame.time.get_ticks()
                    continue
                self.move_count += 1
                if direction == Direction.LEFT:
                    self._facing_left = True
                elif direction == Direction.RIGHT:
                    self._facing_left = False
                if self._last_was_push():
                    self.audio.play_bottle_clank()
                else:
                    self.audio.play_sfx("move")
                if self.board.is_won():
                    self.won = True
                    self._win_elapsed = time.time() - self.start_time
                    self._entering_name = True
                    self.audio.play_sfx("win")
                elif is_lost(self.board.state):
                    self._to_game_over("deadlock")
                    return
            elif action == Action.ABANDON and not self.won:
                self._to_game_over("abandon")
                return
            elif action == Action.UNDO and not self.won:
                if self.board.undo():
                    self.move_count = max(0, self.move_count - 1)
                    self.audio.play_sfx("move")
            elif action == Action.RESET:
                self._reset_session_state()
                self.audio.play_music("game_start", loops=0)
            elif action == Action.SOLVE and not self.won:
                self._confirm_solve = True
                return

    def _handle_solve_confirm(self) -> None:
        """Attend confirmation O/N avant de lancer le solveur."""
        # Filtre pygame : laisser VIDEORESIZE dans la queue (pris par main loop)
        # sinon les resize pendant la confirmation sont avales et l'UI decale.
        for event in pygame.event.get((pygame.QUIT, pygame.KEYDOWN)):
            if event.type == pygame.QUIT:
                self.manager.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_o, pygame.K_y, pygame.K_RETURN):
                    from ui.scenes.solver import SolverScene
                    solver = SolverScene(
                        self.manager, self.level_meta,
                        audio=self.audio,
                        screen_w=self.screen_w, screen_h=self.screen_h,
                    )
                    self.manager.switch(solver)
                    return
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    self._confirm_solve = False

    def _handle_name_input(self) -> None:
        """Gere la saisie du nom du joueur apres victoire."""
        # Filtre pygame : laisser VIDEORESIZE dans la queue (pris par main loop)
        # sinon les resize pendant la saisie sont avales et l'UI decale.
        for event in pygame.event.get((pygame.QUIT, pygame.KEYDOWN, pygame.TEXTINPUT)):
            if event.type == pygame.QUIT:
                self.manager.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self._player_name.strip():
                    save_score(
                        self._player_name.strip(),
                        self.level_meta.name,
                        self.move_count,
                        self._win_elapsed,
                    )
                    self._score_saved = True
                    self._entering_name = False
                    from ui.scenes.ranking import RankingScene
                    ranking = RankingScene(
                        self.manager,
                        level_name=self.level_meta.name,
                        audio=self.audio,
                        screen_w=self.screen_w,
                        screen_h=self.screen_h,
                    )
                    self.manager.switch(ranking)
                    return
                elif event.key == pygame.K_BACKSPACE:
                    self._player_name = self._player_name[:-1]
                elif event.key == pygame.K_ESCAPE:
                    self._entering_name = False
            elif event.type == pygame.TEXTINPUT:
                if len(self._player_name) < 12:
                    self._player_name += event.text

    def _reset_session_state(self) -> None:
        """Remet a zero tous les flags/compteurs pour une nouvelle partie.

        Centralise la reinitialisation pour que tout chemin (RESET manuel,
        reuse ulterieur) parte d'un etat propre ; evite les flags residuels
        (_score_saved, _entering_name, _confirm_solve...) entre deux sessions.
        """
        self.board.reset()
        self.move_count = 0
        self.start_time = time.time()
        self.won = False
        self._entering_name = False
        self._player_name = ""
        self._score_saved = False
        self._confirm_solve = False
        self._invalid_move_shake_start = 0
        self._facing_left = False
        self._game_start_sound_played = False

    def _last_was_push(self) -> bool:
        """Verifie si le dernier mouvement a pousse une caisse."""
        return self.board.was_last_push()

    def _to_game_over(self, reason: str) -> None:
        """Bascule vers GameOverScene avec la raison donnee (deadlock/abandon)."""
        from ui.scenes.game_over import GameOverScene
        frozen = detect_freeze_deadlocks(self.board.state)
        elapsed = time.time() - self.start_time
        self.manager.switch(
            GameOverScene(
                self.manager,
                self.level_meta,
                self.board.state,
                reason,
                self.move_count,
                elapsed,
                frozenset(frozen),
                self.audio,
                screen_w=self.screen_w,
                screen_h=self.screen_h,
            )
        )

    def update(self) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_COLOR)
        assert self._font is not None
        assert self._font_label is not None

        # HUD haut : barre PANEL + 3 champs label/valeur.
        elapsed = self._win_elapsed if self.won else time.time() - self.start_time
        mins, secs = divmod(int(elapsed), 60)
        hud_h = 44
        hud_rect = pygame.Rect(10, 8, self.screen_w - 20, hud_h)
        pygame.draw.rect(screen, HUD_BG, hud_rect, border_radius=10)
        pygame.draw.rect(screen, HUD_BORDER, hud_rect, width=2, border_radius=10)

        fields = [
            ("Niveau", self.level_meta.name),
            ("Coups", str(self.move_count)),
            ("Temps", f"{mins:02d}:{secs:02d}"),
        ]
        col_w = (hud_rect.width - 20) // len(fields)
        for i, (label, value) in enumerate(fields):
            col_x = hud_rect.left + 10 + i * col_w
            lbl = self._font_label.render(f"{label.upper()} :", True, LABEL_COLOR)
            val = self._font.render(value, True, HUD_COLOR)
            screen.blit(lbl, (col_x, hud_rect.top + 6))
            screen.blit(val, (col_x, hud_rect.top + 6 + lbl.get_height()))

        # Grille centree sur panneau CREAM + bordure OLIVE (barre actions reservee en bas).
        board_surface = self.renderer.render(self.board.state, facing_left=self._facing_left)
        bw, bh = board_surface.get_size()
        sy = self.screen_h / 600
        actions_bar_h = max(50, int(60 * sy))
        gx = (self.screen_w - bw) // 2
        board_area_top = 50
        board_area_h = self.screen_h - board_area_top - actions_bar_h
        gy = board_area_top + (board_area_h - bh) // 2
        if self._invalid_move_shake_start:
            elapsed = pygame.time.get_ticks() - self._invalid_move_shake_start
            if elapsed < 200:
                gx += int(math.sin(elapsed * 0.030) * 4)
            else:
                self._invalid_move_shake_start = 0
        pad = 8
        board_frame = pygame.Rect(gx - pad, gy - pad, bw + 2 * pad, bh + 2 * pad)
        pygame.draw.rect(screen, HUD_BG, board_frame, border_radius=10)
        pygame.draw.rect(screen, HUD_BORDER, board_frame, width=2, border_radius=10)
        screen.blit(board_surface, (gx, gy))

        # Barre d'actions PANEL en bas (refonte #244 : remplace le panneau droite).
        actions_bar = pygame.Rect(
            0, self.screen_h - actions_bar_h, self.screen_w, actions_bar_h
        )
        pygame.draw.rect(screen, HUD_BG, actions_bar)
        pygame.draw.line(
            screen, HUD_BORDER,
            (actions_bar.left, actions_bar.top),
            (actions_bar.right, actions_bar.top),
            width=1,
        )
        for btn in self._buttons:
            btn.draw(screen)

        # Confirmation résolution automatique
        if self._confirm_solve:
            confirm_text = "Abandonner la partie ? [O/Y]ui  [N]on"
            confirm_surf = self._font.render(confirm_text, True, INPUT_COLOR)
            overlay_h = confirm_surf.get_height() + 12
            overlay = pygame.Surface((self.screen_w, overlay_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, self.screen_h - 46))
            screen.blit(
                confirm_surf,
                (self.screen_w // 2 - confirm_surf.get_width() // 2, self.screen_h - 40),
            )

        # Message de victoire et saisie du nom
        if self.won:
            overlay_h = 70 if self._entering_name else 30
            overlay_top = self.screen_h - 90
            overlay = pygame.Surface((self.screen_w, overlay_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, overlay_top))

            win_text = f"NIVEAU TERMINÉ ! {self.move_count} coups en {mins:02d}:{secs:02d}"
            win_surf = self._font.render(win_text, True, WIN_COLOR)
            screen.blit(
                win_surf,
                (self.screen_w // 2 - win_surf.get_width() // 2, self.screen_h - 80),
            )
            if self._entering_name:
                prompt = "Entrez votre nom : " + self._player_name + "_"
                prompt_surf = self._font.render(prompt, True, INPUT_COLOR)
                screen.blit(
                    prompt_surf,
                    (self.screen_w // 2 - prompt_surf.get_width() // 2, self.screen_h - 50),
                )
                hint = "[Entrée] Valider  |  [Échap] Passer"
                hint_surf = self._font.render(hint, True, HUD_COLOR)
                screen.blit(
                    hint_surf,
                    (self.screen_w // 2 - hint_surf.get_width() // 2, self.screen_h - 25),
                )