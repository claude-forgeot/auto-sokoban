"""Scene de jeu humain (gameplay interactif)."""

from __future__ import annotations

import time

import pygame

from game.board import Direction
from game.db import save_score
from game.level import LevelMeta, load_level
from ui.audio import AudioManager
from ui.input import Action, Button, poll_events
from ui.fonts import load_font
from ui.renderer import Renderer
from ui.scenes.base import Scene, SceneManager

BG_COLOR = (25, 25, 35)
HUD_COLOR = (220, 220, 220)
WIN_COLOR = (100, 255, 120)
INPUT_COLOR = (255, 255, 200)

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
        panel_w = 160
        hud_h = 50
        available_w = screen_w - panel_w - 40
        available_h = screen_h - hud_h - 20
        cols = self.board.state.width
        rows = self.board.state.height
        adaptive_tile = min(tile_size, available_w // max(cols, 1), available_h // max(rows, 1))
        variant = hash(level_meta.name) % 3
        self.renderer = Renderer(tile_size=max(16, adaptive_tile), variant=variant)
        self.move_count = 0
        self.start_time = 0.0
        self.won = False

        self._font: pygame.font.Font | None = None
        self._buttons: list[Button] = []
        self._entering_name = False
        self._player_name = ""
        self._score_saved = False
        self._win_elapsed = 0.0
        self._confirm_solve = False
        self._facing_left = False

        # MODIFICATION : Flag pour vérifier si le son de début a été joué
        # Cela permet de lancer le son game_start une seule fois au démarrage
        self._game_start_sound_played = False

    def on_enter(self) -> None:
        """Initialise la scene lorsqu'elle devient active.
        
        Cette méthode est appelée au moment où le joueur accède à un nouveau niveau.
        C'est le bon moment pour jouer le son de début de niveau.
        """
        pygame.font.init()
        self._font = load_font(18)

        btn_w, btn_h = 120, 35
        x = self.screen_w - btn_w - 20
        y = 80

        self._buttons = [
            Button(pygame.Rect(x, y, btn_w, btn_h), "ANNULER", Action.UNDO, font=self._font),
            Button(pygame.Rect(x, y + 45, btn_w, btn_h), "RÉINIT.", Action.RESET, font=self._font),
            Button(pygame.Rect(x, y + 90, btn_w, btn_h), "RÉSOUDRE", Action.SOLVE, font=self._font,
                    color=(40, 40, 100), hover_color=(60, 60, 140)),
            Button(pygame.Rect(x, y + 145, btn_w, btn_h), "QUITTER", Action.BACK_MENU, font=self._font,
                    color=(100, 40, 40), hover_color=(140, 60, 60)),
        ]
        self.start_time = time.time()
        
        # MODIFICATION : Jouer le son de début de niveau une seule fois
        # Le flag _game_start_sound_played empêche le son de se rejouer
        # si on quitte et revient dans la même instance de scene
        if not self._game_start_sound_played:
            self.audio.play_game_start()
            self._game_start_sound_played = True

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
                menu = MenuScene(self.manager, screen_w=self.screen_w, screen_h=self.screen_h)
                self.manager.switch(menu)
                return
            elif action in _ACTION_TO_DIR and not self.won:
                direction = _ACTION_TO_DIR[action]
                if self.board.move(direction):
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
            elif action == Action.UNDO and not self.won:
                if self.board.undo():
                    self.move_count = max(0, self.move_count - 1)
                    self.audio.play_sfx("move")
            elif action == Action.RESET:
                # MODIFICATION : Quand on réinitialise le niveau, rejouer le son de début
                self.board.reset()
                self.move_count = 0
                self.start_time = time.time()
                self.won = False
                self._game_start_sound_played = False  # Permet de rejouer le son de début après reset
                self.audio.play_game_start()
            elif action == Action.SOLVE and not self.won:
                self._confirm_solve = True
                return

    def _handle_solve_confirm(self) -> None:
        """Attend confirmation O/N avant de lancer le solveur."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.manager.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_o, pygame.K_y, pygame.K_RETURN):
                    from ui.scenes.solver import SolverScene
                    solver = SolverScene(
                        self.manager, self.level_meta,
                        screen_w=self.screen_w, screen_h=self.screen_h,
                    )
                    self.manager.switch(solver)
                    return
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    self._confirm_solve = False

    def _handle_name_input(self) -> None:
        """Gere la saisie du nom du joueur apres victoire."""
        for event in pygame.event.get():
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

    def _last_was_push(self) -> bool:
        """Verifie si le dernier mouvement a pousse une caisse."""
        return self.board.was_last_push()

    def update(self) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_COLOR)
        assert self._font is not None

        # HUD haut
        elapsed = self._win_elapsed if self.won else time.time() - self.start_time
        mins, secs = divmod(int(elapsed), 60)
        hud_text = f"{self.level_meta.name}  |  Coups: {self.move_count}  |  Temps: {mins:02d}:{secs:02d}"
        hud_surf = self._font.render(hud_text, True, HUD_COLOR)
        screen.blit(hud_surf, (20, 15))

        # Grille centree
        board_surface = self.renderer.render(self.board.state, facing_left=self._facing_left)
        bw, bh = board_surface.get_size()
        panel_w = 160
        available_w = self.screen_w - panel_w
        gx = (available_w - bw) // 2
        gy = 50 + (self.screen_h - 50 - bh) // 2
        screen.blit(board_surface, (gx, gy))

        # Boutons (panneau droite)
        for btn in self._buttons:
            btn.draw(screen)

        # Confirmation résolution automatique
        if self._confirm_solve:
            confirm_text = "Abandonner la partie ? [O]ui / [N]on"
            confirm_surf = self._font.render(confirm_text, True, INPUT_COLOR)
            screen.blit(
                confirm_surf,
                (self.screen_w // 2 - confirm_surf.get_width() // 2, self.screen_h - 40),
            )

        # Message de victoire et saisie du nom
        if self.won:
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