"""Scene de fin de partie (deadlock detecte ou abandon joueur)."""

from __future__ import annotations

import math

import pygame

from game.board import BoardState
from game.level import LevelMeta
from ui.audio import AudioManager
from ui.fonts import load_font
from ui.input import Action, Button, poll_events
from ui.layout import scale_font_size
from ui.renderer import Renderer
from ui.scenes.base import Scene, SceneManager

from ui.colors import (
    BG_GAME_OVER as BG_COLOR,
    DANGER_RED_GAME_OVER as TITLE_COLOR,
)

PANEL_COLOR = (40, 20, 20)
TEXT_COLOR = (230, 210, 210)
MUTED_COLOR = (150, 120, 120)
FROZEN_OVERLAY = (255, 40, 40, 140)  # rouge semi-transparent

REASON_LABELS = {
    "deadlock": "Deadlock détecté : une caisse ne peut plus bouger.",
    "abandon": "Partie abandonnée.",
}


class GameOverScene(Scene):
    """Scene affichee apres deadlock ou abandon manuel."""

    def __init__(
        self,
        manager: SceneManager,
        level_meta: LevelMeta,
        state: BoardState,
        reason: str,
        moves: int,
        elapsed: float,
        frozen_boxes: frozenset[tuple[int, int]],
        audio: AudioManager,
        screen_w: int = 800,
        screen_h: int = 600,
    ) -> None:
        super().__init__(manager)
        self.level_meta = level_meta
        self.state = state
        self.reason = reason
        self.moves = moves
        self.elapsed = elapsed
        self.frozen_boxes = frozen_boxes
        self.audio = audio
        self.screen_w = screen_w
        self.screen_h = screen_h

        self._font_title: pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._buttons: list[Button] = []
        self._preview_surface: pygame.Surface | None = None
        self._preview_tile: int = 0
        self._time_start: int = 0

    def on_enter(self) -> None:
        self._build_layout()
        self._render_preview()
        self._time_start = pygame.time.get_ticks()
        self.audio.play_sfx("game_over")

    def on_resize(self, new_w: int, new_h: int) -> None:
        self.screen_w = new_w
        self.screen_h = new_h
        self._build_layout()
        self._render_preview()

    def _build_layout(self) -> None:
        self._font_title = load_font(scale_font_size(32, self.screen_h), bold=True)
        self._font_normal = load_font(scale_font_size(18, self.screen_h))
        self._font_small = load_font(scale_font_size(13, self.screen_h))

        btn_w = max(180, int(self.screen_w * 0.28))
        btn_h = max(32, int(self.screen_h * 0.07))
        x = self.screen_w // 2 - btn_w // 2
        spacing = btn_h + int(self.screen_h * 0.02)
        y0 = self.screen_h - int(self.screen_h * 0.30)
        self._buttons = [
            Button(
                pygame.Rect(x, y0, btn_w, btn_h),
                "REJOUER",
                Action.RESET,
                font=self._font_normal,
                color=(40, 100, 40),
                hover_color=(60, 140, 60),
            ),
            Button(
                pygame.Rect(x, y0 + spacing, btn_w, btn_h),
                "CHOISIR UN NIVEAU",
                Action.PLAY,
                font=self._font_normal,
                color=(40, 60, 100),
                hover_color=(60, 90, 140),
            ),
            Button(
                pygame.Rect(x, y0 + spacing * 2, btn_w, btn_h),
                "MENU",
                Action.BACK_MENU,
                font=self._font_normal,
                color=(100, 40, 40),
                hover_color=(140, 60, 60),
            ),
        ]

    def _render_preview(self) -> None:
        """Rend le plateau fige (base sans overlay, l'overlay est anime a chaque draw)."""
        max_preview_w = max(240, int(self.screen_w * 0.50))
        max_preview_h = max(160, int(self.screen_h * 0.40))
        cols = max(self.state.width, 1)
        rows = max(self.state.height, 1)
        tile = max(16, min(max_preview_w // cols, max_preview_h // rows))
        self._preview_tile = tile
        renderer = Renderer(tile_size=tile)
        self._preview_surface = renderer.render(self.state)

    # -------- events --------

    def handle_events(self) -> None:
        actions = poll_events(self._buttons, audio=self.audio)
        for action in actions:
            if action == Action.QUIT:
                self.manager.quit()
                return
            if action == Action.RESET:
                self._replay()
                return
            if action == Action.PLAY:
                self._choose_level()
                return
            if action in (Action.BACK_MENU,):
                self._to_menu()
                return

    def _replay(self) -> None:
        from ui.scenes.game import GameScene
        self.manager.switch(
            GameScene(
                self.manager, self.level_meta, self.audio,
                screen_w=self.screen_w, screen_h=self.screen_h,
            )
        )

    def _choose_level(self) -> None:
        from ui.scenes import Mode
        from ui.scenes.level_select import LevelSelectScene
        self.manager.switch(
            LevelSelectScene(
                self.manager, mode=Mode.PLAY, audio=self.audio,
                screen_w=self.screen_w, screen_h=self.screen_h,
            )
        )

    def _to_menu(self) -> None:
        from ui.scenes.menu import MenuScene
        self.manager.switch(
            MenuScene(self.manager, screen_w=self.screen_w, screen_h=self.screen_h)
        )

    def update(self) -> None:
        pass

    def _draw_frozen_overlay(self, screen: pygame.Surface, px: int, py: int) -> None:
        """Blitte un overlay rouge pulsant sur chaque caisse bloquee."""
        if not self.frozen_boxes or self._preview_tile <= 0:
            return
        elapsed = (pygame.time.get_ticks() - self._time_start) / 1000.0
        # Pulsation sinus : alpha varie entre 80 et 180, periode ~0.9 s.
        pulse = (math.sin(elapsed * 2 * math.pi / 0.9) + 1) / 2  # [0, 1]
        alpha = int(80 + 100 * pulse)
        tile = self._preview_tile
        overlay = pygame.Surface((tile, tile), pygame.SRCALPHA)
        overlay.fill((255, 40, 40, alpha))
        border_col = (255, int(60 + 120 * pulse), int(60 + 60 * pulse))
        for r, c in self.frozen_boxes:
            dst = (px + c * tile, py + r * tile)
            screen.blit(overlay, dst)
            pygame.draw.rect(screen, border_col, (*dst, tile, tile), width=2)

    # -------- draw --------

    def draw(self, screen: pygame.Surface) -> None:
        assert self._font_title is not None
        assert self._font_normal is not None
        assert self._font_small is not None

        screen.fill(BG_COLOR)

        # Titre.
        title = self._font_title.render("GAME OVER", False, TITLE_COLOR)
        screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 20))

        # Raison.
        reason_text = REASON_LABELS.get(self.reason, self.reason)
        reason_surf = self._font_normal.render(reason_text, True, TEXT_COLOR)
        screen.blit(reason_surf, (self.screen_w // 2 - reason_surf.get_width() // 2, 70))

        # Stats.
        mins, secs = divmod(int(self.elapsed), 60)
        stats_text = f"Niveau : {self.level_meta.name}  |  Coups : {self.moves}  |  Temps : {mins:02d}:{secs:02d}"
        stats_surf = self._font_small.render(stats_text, True, MUTED_COLOR)
        screen.blit(stats_surf, (self.screen_w // 2 - stats_surf.get_width() // 2, 100))

        # Preview plateau fige + overlay pulsant sur caisses frozen.
        if self._preview_surface is not None:
            pw, ph = self._preview_surface.get_size()
            px = self.screen_w // 2 - pw // 2
            py = 130
            # Cadre rouge autour de la preview.
            pygame.draw.rect(screen, (80, 20, 20), (px - 6, py - 6, pw + 12, ph + 12))
            screen.blit(self._preview_surface, (px, py))
            self._draw_frozen_overlay(screen, px, py)

        # Boutons.
        for btn in self._buttons:
            btn.draw(screen)
