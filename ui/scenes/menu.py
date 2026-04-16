"""Scene du menu principal."""

from __future__ import annotations

from pathlib import Path

import pygame

from game.level import LevelMeta, list_levels
from ui.audio import AudioManager
from ui.input import Action, Button, poll_events
from ui.scenes.base import Scene, SceneManager

# Couleurs
BG_COLOR = (25, 25, 35)
TITLE_COLOR = (255, 220, 80)
TEXT_COLOR = (220, 220, 220)
SELECTED_COLOR = (100, 180, 255)
MUTED_COLOR = (120, 120, 120)


class MenuScene(Scene):
    """Menu principal : titre, selection niveau, boutons d'action."""

    def __init__(
        self,
        manager: SceneManager,
        screen_w: int = 800,
        screen_h: int = 600,
        levels_dir: str | Path = "levels",
    ) -> None:
        super().__init__(manager)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.levels = list_levels(levels_dir)
        self.selected_level: int = 0
        self.music_on = True
        self.audio = AudioManager()

        self._font_title: pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._buttons: list[Button] = []
        self._action_callback: dict[Action, str] = {}

    def on_enter(self) -> None:
        pygame.font.init()
        self._font_title = pygame.font.SysFont("monospace", 36, bold=True)
        self._font_normal = pygame.font.SysFont("monospace", 18)

        btn_w, btn_h = 200, 40
        x = self.screen_w // 2 - btn_w // 2
        y_start = 380

        self._buttons = [
            Button(
                pygame.Rect(x, y_start, btn_w, btn_h),
                "JOUER",
                Action.PLAY,
                font=self._font_normal,
                color=(40, 100, 40),
                hover_color=(60, 140, 60),
            ),
            Button(
                pygame.Rect(x, y_start + 50, btn_w, btn_h),
                "RESOUDRE AUTO",
                Action.SOLVE,
                font=self._font_normal,
                color=(40, 40, 100),
                hover_color=(60, 60, 140),
            ),
            Button(
                pygame.Rect(x, y_start + 100, btn_w, btn_h),
                "CLASSEMENT",
                Action.RANKING,
                font=self._font_normal,
                color=(80, 60, 20),
                hover_color=(120, 90, 30),
            ),
            Button(
                pygame.Rect(x, y_start + 150, btn_w, btn_h),
                "QUITTER",
                Action.QUIT,
                font=self._font_normal,
                color=(100, 40, 40),
                hover_color=(140, 60, 60),
            ),
        ]

        self.audio.load()
        if self.music_on:
            self.audio.play_music()

    def handle_events(self) -> None:
        actions = poll_events(self._buttons)
        for action in actions:
            if action == Action.QUIT:
                self.manager.quit()
            elif action == Action.PLAY:
                self._start_game()
            elif action == Action.MOVE_UP:
                if self.selected_level > 0:
                    self.selected_level -= 1
            elif action == Action.MOVE_DOWN:
                if self.selected_level < len(self.levels) - 1:
                    self.selected_level += 1
            elif action == Action.SOLVE:
                self._start_solver()
            elif action == Action.RANKING:
                self._show_ranking()
            elif action == Action.PAUSE:
                self._toggle_music()

    def _start_game(self) -> None:
        """Transition vers la scene de jeu."""
        level = self.get_selected_level()
        if level is None:
            return
        from ui.scenes.game import GameScene

        scene = GameScene(
            self.manager, level, self.audio,
            screen_w=self.screen_w, screen_h=self.screen_h,
        )
        self.manager.switch(scene)

    def _start_solver(self) -> None:
        """Transition vers la scene de resolution automatique."""
        level = self.get_selected_level()
        if level is None:
            return
        from ui.scenes.solver import SolverScene

        scene = SolverScene(
            self.manager, level,
            screen_w=self.screen_w, screen_h=self.screen_h,
        )
        self.manager.switch(scene)

    def _show_ranking(self) -> None:
        """Transition vers la scene de classement."""
        from ui.scenes.ranking import RankingScene

        scene = RankingScene(
            self.manager,
            screen_w=self.screen_w,
            screen_h=self.screen_h,
        )
        self.manager.switch(scene)

    def _toggle_music(self) -> None:
        self.music_on = not self.music_on
        if self.music_on:
            self.audio.unpause_music()
        else:
            self.audio.pause_music()

    def update(self) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_COLOR)
        assert self._font_title is not None
        assert self._font_normal is not None

        # Titre
        title = self._font_title.render("AUTO-SOKOBAN", True, TITLE_COLOR)
        screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 30))

        # Liste des niveaux
        y = 100
        header = self._font_normal.render(
            "Selectionnez un niveau :", True, TEXT_COLOR
        )
        screen.blit(header, (self.screen_w // 2 - header.get_width() // 2, y))
        y += 30

        for i, level in enumerate(self.levels):
            color = SELECTED_COLOR if i == self.selected_level else TEXT_COLOR
            prefix = ">" if i == self.selected_level else " "
            text = f"{prefix} {level.name} ({level.difficulty}, {level.box_count} caisses)"
            rendered = self._font_normal.render(text, True, color)
            screen.blit(
                rendered, (self.screen_w // 2 - rendered.get_width() // 2, y)
            )
            y += 24

        # Boutons
        for btn in self._buttons:
            btn.draw(screen)

        # Footer musique
        music_text = f"[ESPACE] Musique : {'ON' if self.music_on else 'OFF'}"
        music_rendered = self._font_normal.render(music_text, True, MUTED_COLOR)
        screen.blit(
            music_rendered,
            (self.screen_w // 2 - music_rendered.get_width() // 2, self.screen_h - 40),
        )

    def get_selected_level(self) -> LevelMeta | None:
        """Retourne le niveau selectionne ou None si aucun niveau."""
        if not self.levels:
            return None
        return self.levels[self.selected_level]
