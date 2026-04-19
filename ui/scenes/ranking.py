"""Scene d'affichage du classement."""

from __future__ import annotations

import pygame

from game.db import ScoreEntry, get_all_ranking, get_ranking
from ui.audio import AudioManager
from ui.input import Action, Button, poll_events
from ui.scenes.base import Scene, SceneManager

BG_COLOR = (25, 25, 35)
TITLE_COLOR = (255, 220, 80)
TEXT_COLOR = (220, 220, 220)
HEADER_COLOR = (180, 180, 180)
HIGHLIGHT_COLOR = (100, 255, 120)
RANK_COLORS = [(255, 215, 0), (192, 192, 192), (205, 127, 50)]  # or, argent, bronze


class RankingScene(Scene):
    """Affiche le classement pour un niveau ou global."""

    def __init__(
        self,
        manager: SceneManager,
        level_name: str | None = None,
        audio: AudioManager | None = None,
        screen_w: int = 800,
        screen_h: int = 600,
    ) -> None:
        super().__init__(manager)
        self.level_name = level_name
        self.audio = audio
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._entries: list[ScoreEntry] = []

        self._font: pygame.font.Font | None = None
        self._font_title: pygame.font.Font | None = None
        self._buttons: list[Button] = []

    def on_enter(self) -> None:
        pygame.font.init()
        from ui.fonts import load_font
        from ui.layout import scale_font_size
        self._font_title = load_font(scale_font_size(28, self.screen_h), bold=True)
        self._font = load_font(scale_font_size(16, self.screen_h))

        if self.level_name:
            self._entries = get_ranking(self.level_name, limit=10)
        else:
            self._entries = get_all_ranking(limit=15)

        self._build_buttons()

    def _build_buttons(self) -> None:
        assert self._font is not None
        btn_w, btn_h = 180, 35
        x = self.screen_w // 2 - btn_w // 2
        self._buttons = [
            Button(
                pygame.Rect(x, self.screen_h - 60, btn_w, btn_h),
                "RETOUR MENU",
                Action.BACK_MENU,
                font=self._font,
                color=(100, 40, 40),
                hover_color=(140, 60, 60),
            ),
        ]

    def on_resize(self, new_w: int, new_h: int) -> None:
        self.screen_w = new_w
        self.screen_h = new_h
        if self._font is not None:
            self._build_buttons()

    def handle_events(self) -> None:
        actions = poll_events(self._buttons, audio=self.audio)
        for action in actions:
            if action in (Action.QUIT, Action.BACK_MENU):
                from ui.scenes.menu import MenuScene

                menu = MenuScene(
                    self.manager,
                    screen_w=self.screen_w,
                    screen_h=self.screen_h,
                )
                self.manager.switch(menu)
                return

    def update(self) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_COLOR)
        assert self._font_title is not None
        assert self._font is not None

        # Titre
        if self.level_name:
            title_text = f"Classement : {self.level_name}"
        else:
            title_text = "Classement global"
        title = self._font_title.render(title_text, True, TITLE_COLOR)
        screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 20))

        # En-tete du tableau
        y = 80
        header = f"{'#':>3}  {'Joueur':<12} {'Niveau':<15} {'Coups':>6} {'Temps':>8} {'Date':<16}"
        header_surf = self._font.render(header, True, HEADER_COLOR)
        screen.blit(header_surf, (40, y))
        y += 5
        pygame.draw.line(screen, HEADER_COLOR, (40, y + 16), (self.screen_w - 40, y + 16))
        y += 22

        # Entrees
        if not self._entries:
            empty = self._font.render("Aucun score enregistre.", True, TEXT_COLOR)
            screen.blit(empty, (self.screen_w // 2 - empty.get_width() // 2, y + 30))
        else:
            for i, entry in enumerate(self._entries):
                rank = i + 1
                mins, secs = divmod(int(entry.time_s), 60)
                color = RANK_COLORS[i] if i < 3 else TEXT_COLOR
                line = (
                    f"{rank:>3}  {entry.player:<12} {entry.level:<15} "
                    f"{entry.moves:>6} {mins:02d}:{secs:02d}   {entry.date:<16}"
                )
                line_surf = self._font.render(line, True, color)
                screen.blit(line_surf, (40, y))
                y += 22

        # Boutons
        for btn in self._buttons:
            btn.draw(screen)
