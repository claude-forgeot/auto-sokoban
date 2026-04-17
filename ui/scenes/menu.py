"""Scene du menu principal avec fond pixel-art et vignettes miniatures."""

from __future__ import annotations

from pathlib import Path

import pygame

from game.level import LevelMeta, list_levels, load_level
from ui.audio import AudioManager
from ui.fonts import load_font
from ui.input import Action, Button, poll_events
from ui.renderer import Renderer
from ui.scenes.base import Scene, SceneManager

# Couleurs
BG_COLOR = (25, 25, 35)
TITLE_COLOR = (255, 220, 80)
TEXT_COLOR = (220, 220, 220)
SELECTED_COLOR = (100, 180, 255)
MUTED_COLOR = (120, 120, 120)
HIGHLIGHT_BORDER = (100, 180, 255)

# Grille niveaux (2 colonnes)
GRID_COLS = 2
GRID_X = 50
GRID_Y = 80
CELL_W = 350
CELL_H = 68
THUMB_AREA_W = 96


class MenuScene(Scene):
    """Menu principal avec fond pixel-art, vignettes miniatures et boutons animés."""

    def __init__(
        self,
        manager: SceneManager,
        screen_w: int = 800,
        screen_h: int = 600,
        levels_dir: str | Path | None = None,
    ) -> None:
        super().__init__(manager)
        self.screen_w = screen_w
        self.screen_h = screen_h
        _default_levels = Path(__file__).resolve().parent.parent.parent / "levels"
        self.levels = list_levels(levels_dir if levels_dir is not None else _default_levels)
        self.selected_level: int = 0
        self.music_on = True
        self.audio = AudioManager()

        self._font_title: pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._buttons: list[Button] = []
        self._level_rects: list[pygame.Rect] = []

        # Vignettes et fond
        self._thumb_renderer = Renderer(tile_size=12)
        self._thumbnails: list[pygame.Surface] = []
        self._bg_cache: pygame.Surface | None = None
        self._bg_level_idx: int = -1

    def on_enter(self) -> None:
        self._font_title = load_font(32, bold=True)
        self._font_normal = load_font(16)
        self._font_small = load_font(13)

        self._load_thumbnails()

        # Position boutons sous la grille de niveaux
        n_rows = (len(self.levels) + GRID_COLS - 1) // GRID_COLS if self.levels else 1
        btn_y_start = GRID_Y + n_rows * CELL_H + 16
        btn_w, btn_h = 200, 36
        x = self.screen_w // 2 - btn_w // 2
        spacing = 42

        self._buttons = [
            Button(
                pygame.Rect(x, btn_y_start, btn_w, btn_h),
                "JOUER",
                Action.PLAY,
                font=self._font_normal,
                color=(40, 100, 40),
                hover_color=(60, 140, 60),
            ),
            Button(
                pygame.Rect(x, btn_y_start + spacing, btn_w, btn_h),
                "RÉSOUDRE AUTO",
                Action.SOLVE,
                font=self._font_normal,
                color=(40, 40, 100),
                hover_color=(60, 60, 140),
            ),
            Button(
                pygame.Rect(x, btn_y_start + spacing * 2, btn_w, btn_h),
                "COURSE ALGO",
                Action.RACE,
                font=self._font_normal,
                color=(80, 40, 100),
                hover_color=(120, 60, 140),
            ),
            Button(
                pygame.Rect(x, btn_y_start + spacing * 3, btn_w, btn_h),
                "CLASSEMENT",
                Action.RANKING,
                font=self._font_normal,
                color=(80, 60, 20),
                hover_color=(120, 90, 30),
            ),
            Button(
                pygame.Rect(x, btn_y_start + spacing * 4, btn_w, btn_h),
                "QUITTER",
                Action.QUIT,
                font=self._font_normal,
                color=(100, 40, 40),
                hover_color=(140, 60, 60),
            ),
        ]

        # Zones cliquables pour la grille des niveaux
        self._level_rects = []
        for i in range(len(self.levels)):
            col = i % GRID_COLS
            row = i // GRID_COLS
            rx = GRID_X + col * CELL_W
            ry = GRID_Y + row * CELL_H
            self._level_rects.append(pygame.Rect(rx, ry, CELL_W, CELL_H))

        self.audio.load()
        if self.music_on:
            self.audio.play_music()

    def _load_thumbnails(self) -> None:
        """Charge les vignettes miniatures de chaque niveau."""
        self._thumbnails = []
        for level in self.levels:
            board = load_level(level.path)
            self._thumbnails.append(self._thumb_renderer.render(board.state))

    def _get_background(self) -> pygame.Surface:
        """Retourne le fond avec le plateau du niveau sélectionné, assombri."""
        if self._bg_level_idx == self.selected_level and self._bg_cache is not None:
            return self._bg_cache

        bg = pygame.Surface((self.screen_w, self.screen_h))
        bg.fill(BG_COLOR)

        if self.levels:
            self._bg_level_idx = self.selected_level
            level = self.levels[self.selected_level]
            board = load_level(level.path)
            state = board.state

            max_tile = min(
                self.screen_w // max(state.width, 1),
                self.screen_h // max(state.height, 1),
            )
            bg_renderer = Renderer(tile_size=max(16, max_tile))
            board_surf = bg_renderer.render(state)

            bw, bh = board_surf.get_size()
            bg.blit(board_surf, ((self.screen_w - bw) // 2, (self.screen_h - bh) // 2))

            overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            bg.blit(overlay, (0, 0))

        self._bg_cache = bg
        return bg

    def handle_events(self) -> None:
        result = poll_events(self._buttons, audio=self.audio)

        # Clics sur la liste des niveaux
        for cx, cy in result.clicks:
            for i, rect in enumerate(self._level_rects):
                if rect.collidepoint(cx, cy):
                    self.selected_level = i
                    break

        for action in result:
            if action in (Action.QUIT, Action.BACK_MENU):
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
            elif action == Action.RACE:
                self._start_race()
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
        """Transition vers la scene de resolution automatique.
        
        L'import de SolverScene est fait ici pour eviter une importation circulaire.
        """
        level = self.get_selected_level()
        if level is None:
            return
        # MODIFICATION : Import local pour eviter une boucle circulaire
        from ui.scenes.solver import SolverScene

        scene = SolverScene(
            self.manager, level, self.audio,
            screen_w=self.screen_w, screen_h=self.screen_h,
        )
        self.manager.switch(scene)

    def _start_race(self) -> None:
        """Transition vers la scene de course algorithmique."""
        level = self.get_selected_level()
        if level is None:
            return
        from ui.scenes.race import RaceScene

        scene = RaceScene(
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
        assert self._font_title is not None
        assert self._font_normal is not None
        assert self._font_small is not None

        # Fond : plateau assombri
        screen.blit(self._get_background(), (0, 0))

        # Titre (antialias=False pour le rendu pixel)
        title = self._font_title.render("AUTO-SOKOBAN", False, TITLE_COLOR)
        screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 12))

        # Sous-titre
        header = self._font_small.render(
            "Sélectionnez un niveau :", True, MUTED_COLOR
        )
        screen.blit(header, (GRID_X, GRID_Y - 16))

        # Grille des niveaux avec vignettes
        if not self.levels:
            no_level = self._font_normal.render(
                "Aucun niveau trouvé dans levels/", True, MUTED_COLOR
            )
            screen.blit(no_level, (self.screen_w // 2 - no_level.get_width() // 2, GRID_Y + 10))

        for i, level in enumerate(self.levels):
            col = i % GRID_COLS
            row = i // GRID_COLS
            cx = GRID_X + col * CELL_W
            cy = GRID_Y + row * CELL_H

            # Cadre de sélection
            if i == self.selected_level:
                sel_rect = pygame.Rect(cx - 2, cy - 2, CELL_W - 8, CELL_H)
                pygame.draw.rect(screen, HIGHLIGHT_BORDER, sel_rect, width=2, border_radius=4)

            # Vignette miniature
            if i < len(self._thumbnails):
                thumb = self._thumbnails[i]
                _, th = thumb.get_size()
                ty = cy + (CELL_H - 4 - th) // 2
                tx = cx + 4
                screen.blit(thumb, (tx, ty))

            # Nom et info du niveau
            text_x = cx + THUMB_AREA_W + 8
            color = SELECTED_COLOR if i == self.selected_level else TEXT_COLOR
            name_surf = self._font_normal.render(level.name, True, color)
            screen.blit(name_surf, (text_x, cy + 10))

            info = f"{level.difficulty} - {level.box_count} caisses"
            info_surf = self._font_small.render(info, True, MUTED_COLOR)
            screen.blit(info_surf, (text_x, cy + 32))

        # Boutons
        for btn in self._buttons:
            btn.draw(screen)

        # Footer musique
        icon = ">>" if self.music_on else "||"
        music_text = f"[ESPACE] [{icon}] Musique : {'ON' if self.music_on else 'OFF'}"
        music_rendered = self._font_small.render(music_text, True, MUTED_COLOR)
        screen.blit(
            music_rendered,
            (self.screen_w // 2 - music_rendered.get_width() // 2, self.screen_h - 30),
        )

    def get_selected_level(self) -> LevelMeta | None:
        """Retourne le niveau selectionne ou None si aucun niveau."""
        if not self.levels:
            return None
        return self.levels[self.selected_level]
