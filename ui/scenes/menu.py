"""Scene du menu principal : 5 actions, selection niveau deleguee a LevelSelectScene."""

from __future__ import annotations

from pathlib import Path

import pygame

from ui.audio import AudioManager
from ui.fonts import load_font, load_serif
from ui.input import Action, Button, poll_events
from ui.layout import scale_font_size
from ui.scenes import Mode
from ui.scenes.base import Scene, SceneManager

from ui.colors import (
    BG as BG_COLOR,
    SAGE_DARK as TITLE_COLOR,
    BROWN as SUBTITLE_COLOR,
    OLIVE as MUTED_COLOR,
)

_BG_IMAGE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "assets" / "ui" / "bg_cottagecore.png"
)


class MenuScene(Scene):
    """Menu principal : 5 boutons (JOUER, RÉSOUDRE, COURSE, CLASSEMENT, QUITTER).

    La sélection du niveau est déléguée à LevelSelectScene, atteinte via les
    actions PLAY / SOLVE / RACE.
    """

    def __init__(
        self,
        manager: SceneManager,
        audio: AudioManager,
        screen_w: int = 800,
        screen_h: int = 600,
    ) -> None:
        super().__init__(manager)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.music_on = True
        self.audio = audio

        self._font_title: pygame.font.Font | None = None
        self._font_subtitle: pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._buttons: list[Button] = []
        self._bg_surface: pygame.Surface | None = None

    def on_enter(self) -> None:
        self._build_layout()
        self._load_bg()
        if self.music_on:
            self.audio.play_music()

    def on_resize(self, new_w: int, new_h: int) -> None:
        self.screen_w = new_w
        self.screen_h = new_h
        self._build_layout()
        self._load_bg()

    def _load_bg(self) -> None:
        if _BG_IMAGE_PATH.exists():
            raw = pygame.image.load(str(_BG_IMAGE_PATH)).convert()
            self._bg_surface = pygame.transform.smoothscale(
                raw, (self.screen_w, self.screen_h)
            )
        else:
            self._bg_surface = None

    def _build_layout(self) -> None:
        self._font_title = load_serif(scale_font_size(42, self.screen_h), weight="bold")
        self._font_subtitle = load_serif(
            scale_font_size(16, self.screen_h), italic=True
        )
        self._font_normal = load_font(scale_font_size(16, self.screen_h))
        self._font_small = load_font(scale_font_size(13, self.screen_h))

        specs = [
            ("JOUER", Action.PLAY, "primary"),
            ("RÉSOUDRE AUTO", Action.SOLVE, "solve"),
            ("COURSE ALGO", Action.RACE, "race"),
            ("CLASSEMENT", Action.RANKING, "rank"),
            ("QUITTER", Action.QUIT, "quit"),
        ]

        padding_x = scale_font_size(24, self.screen_h)
        max_label_w = max(self._font_normal.size(label)[0] for label, _, _ in specs)
        btn_w = max(scale_font_size(200, self.screen_h), max_label_w + padding_x * 2)
        btn_w = min(btn_w, self.screen_w - scale_font_size(80, self.screen_h))
        btn_h = max(36, scale_font_size(40, self.screen_h))
        spacing = btn_h + 14

        total_h = len(specs) * spacing - (spacing - btn_h)
        start_y = max(
            scale_font_size(160, self.screen_h),
            (self.screen_h - total_h) // 2 + scale_font_size(20, self.screen_h),
        )
        x = self.screen_w // 2 - btn_w // 2

        self._buttons = [
            Button(
                pygame.Rect(x, start_y + i * spacing, btn_w, btn_h),
                label,
                action,
                font=self._font_normal,
                variant=variant,
            )
            for i, (label, action, variant) in enumerate(specs)
        ]

    def handle_events(self) -> None:
        result = poll_events(self._buttons, audio=self.audio)
        for action in result:
            if action == Action.QUIT:
                self.manager.quit()
            elif action == Action.PLAY:
                self._open_level_select(Mode.PLAY)
            elif action == Action.SOLVE:
                self._open_level_select(Mode.SOLVE)
            elif action == Action.RACE:
                self._open_level_select(Mode.RACE)
            elif action == Action.RANKING:
                self._show_ranking()
            elif action == Action.PAUSE:
                self._toggle_music()
            elif action == Action.BACK_MENU:
                self.manager.quit()

    def _open_level_select(self, mode: Mode) -> None:
        from ui.scenes.level_select import LevelSelectScene

        self.manager.switch(
            LevelSelectScene(
                self.manager,
                mode=mode,
                screen_w=self.screen_w,
                screen_h=self.screen_h,
                audio=self.audio,
            )
        )

    def _show_ranking(self) -> None:
        from ui.scenes.ranking import RankingScene

        self.manager.switch(
            RankingScene(
                self.manager,
                audio=self.audio,
                screen_w=self.screen_w,
                screen_h=self.screen_h,
            )
        )

    def _toggle_music(self) -> None:
        self.music_on = not self.music_on
        if self.music_on:
            self.audio.unpause_music()
        else:
            self.audio.pause_music()

    def update(self) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        assert self._font_title is not None
        assert self._font_subtitle is not None
        assert self._font_normal is not None
        assert self._font_small is not None

        if self._bg_surface is not None:
            screen.blit(self._bg_surface, (0, 0))
        else:
            screen.fill(BG_COLOR)

        title = self._font_title.render("AUTO-SOKOBAN", True, TITLE_COLOR)
        screen.blit(
            title,
            (self.screen_w // 2 - title.get_width() // 2, scale_font_size(50, self.screen_h)),
        )

        subtitle = self._font_subtitle.render(
            "Puzzle + solveurs automatiques (BFS / DFS / A*)",
            True,
            SUBTITLE_COLOR,
        )
        screen.blit(
            subtitle,
            (
                self.screen_w // 2 - subtitle.get_width() // 2,
                scale_font_size(110, self.screen_h),
            ),
        )

        for btn in self._buttons:
            btn.draw(screen)

        icon = ">>" if self.music_on else "||"
        music_text = f"[ESPACE] [{icon}] Musique : {'ON' if self.music_on else 'OFF'}"
        music_rendered = self._font_small.render(music_text, True, MUTED_COLOR)
        screen.blit(
            music_rendered,
            (
                self.screen_w // 2 - music_rendered.get_width() // 2,
                self.screen_h - scale_font_size(30, self.screen_h),
            ),
        )
