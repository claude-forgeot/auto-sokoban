"""Selecteur de niveaux avec onglets difficulte + grille + preview.

Layout L2 (800x600 statique, resize couvert par tache #127) :
- Onglets haut : 50 px (FACILE / MOYEN / DIFFICILE).
- Grille gauche : ~55% largeur, vignettes 120x90 en 3 colonnes.
- Preview droite : ~40% largeur, apercu grand format du niveau selectionne.
- Actions bas : 60 px (RETOUR / LANCER).
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pygame

from game.db import get_best_for_level, get_completed_levels
from game.level import LevelMeta, list_levels, load_level
from ui.audio import AudioManager
from ui.fonts import load_font, load_mono, load_serif
from ui.input import Action, Button, poll_events
from ui.layout import BASE_H, BASE_W, scale_font_size
from ui.renderer import Renderer
from ui.scenes import Mode
from ui.scenes.base import Scene, SceneManager

from ui.colors import (
    BG as BG_COLOR,
    SAGE_DARK as TITLE_COLOR,
    INK as TEXT_COLOR,
    OLIVE as MUTED_COLOR,
    TERRACOTTA as HIGHLIGHT_BORDER,
    SEPARATOR,
    PANEL as PANEL_COLOR,
    CREAM,
    SAGE,
    OLIVE_DARK,
)

TAB_ACTIVE_COLOR = SAGE
TAB_INACTIVE_COLOR = CREAM
COMPLETED_MARK_COLOR = SAGE
PENDING_STATUS_COLOR = OLIVE_DARK

# Dimensions layout (800x600)
TAB_BAR_H = 50
ACTIONS_BAR_H = 60
GRID_PANEL_W = 440  # ~55% de 800
PREVIEW_PANEL_W = 360  # ~40% de 800 (le reste)
GRID_COLS = 3
THUMB_W = 120
THUMB_H = 90
CELL_PAD_X = 10
CELL_PAD_Y = 14
GRID_X_ORIGIN = 10
GRID_Y_ORIGIN = TAB_BAR_H + 12

DIFFICULTIES = ("facile", "moyen", "difficile")

MODE_TITLES = {
    Mode.PLAY: "CHOISIR UN NIVEAU",
    Mode.SOLVE: "CHOISIR NIVEAU À RÉSOUDRE",
    Mode.RACE: "CHOISIR NIVEAU POUR COURSE",
}

MODE_LAUNCH_LABELS = {
    Mode.PLAY: "LANCER",
    Mode.SOLVE: "RÉSOUDRE",
    Mode.RACE: "LANCER COURSE",
}


class LevelSelectScene(Scene):
    """Scene de selection de niveau avec onglets de difficulte."""

    def __init__(
        self,
        manager: SceneManager,
        audio: AudioManager,
        mode: Mode = Mode.PLAY,
        screen_w: int = 800,
        screen_h: int = 600,
        levels_dir: str | Path | None = None,
    ) -> None:
        super().__init__(manager)
        self.mode = mode
        self.screen_w = screen_w
        self.screen_h = screen_h
        _default_levels = Path(__file__).resolve().parent.parent.parent / "levels"
        all_levels = list_levels(levels_dir if levels_dir is not None else _default_levels)

        # Regroupement par difficulte.
        self.levels_by_difficulty: dict[str, list[LevelMeta]] = {d: [] for d in DIFFICULTIES}
        for lvl in all_levels:
            if lvl.difficulty in self.levels_by_difficulty:
                self.levels_by_difficulty[lvl.difficulty].append(lvl)

        # Etat courant.
        self._active_difficulty_idx = 0  # index dans DIFFICULTIES
        self._selected_in_tab: dict[str, int] = {d: 0 for d in DIFFICULTIES}
        self._scroll_offset = 0

        self.audio = audio

        # Donnees BDD (chargees en on_enter).
        self._completed: set[str] = set()
        self._best: dict[str, tuple[int, float] | None] = {}

        # Ressources.
        self._font_title: pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._tab_buttons: list[Button] = []
        self._action_buttons: list[Button] = []
        self._cell_rects: list[pygame.Rect] = []  # recalcule a chaque draw
        self._thumb_renderer = Renderer(tile_size=8)
        self._thumbnails: dict[str, pygame.Surface] = {}  # level.name -> surface
        self._last_click_time = 0
        self._last_click_idx = -1

    # -------- lifecycle --------

    def on_enter(self) -> None:
        self._completed = get_completed_levels()
        self._best = {
            lvl.name: get_best_for_level(lvl.name)
            for lvls in self.levels_by_difficulty.values()
            for lvl in lvls
        }

        self._build_layout()
        self._load_thumbnails()

    def on_resize(self, new_w: int, new_h: int) -> None:
        self.screen_w = new_w
        self.screen_h = new_h
        self._build_layout()
        # Cle du LRU = (path, w, h) ; chaque resize change (w, h) pour la preview
        # et pollue le cache avec d'anciennes tailles devenues inutiles.
        _render_thumbnail.cache_clear()
        self._load_thumbnails()

    def _build_layout(self) -> None:
        self._font_title = load_serif(scale_font_size(28, self.screen_h), weight="bold")
        self._font_normal = load_font(scale_font_size(16, self.screen_h))
        self._font_small = load_mono(scale_font_size(12, self.screen_h))
        self._build_tab_buttons()
        self._build_action_buttons()

    def _sx(self) -> float:
        return self.screen_w / BASE_W

    def _sy(self) -> float:
        return self.screen_h / BASE_H

    def _scaled(self, v: int, vertical: bool = False) -> int:
        """Scale une valeur px (horizontal par defaut)."""
        return max(1, int(round(v * (self._sy() if vertical else self._sx()))))

    def _load_thumbnails(self) -> None:
        """Charge les vignettes de tous les niveaux (cache par path)."""
        self._thumbnails = {}
        for levels in self.levels_by_difficulty.values():
            for lvl in levels:
                surf = _render_thumbnail(lvl.path, THUMB_W, THUMB_H)
                self._thumbnails[lvl.name] = surf

    def _build_tab_buttons(self) -> None:
        self._tab_buttons = []
        tab_w = self.screen_w // len(DIFFICULTIES)
        tab_h = self._scaled(TAB_BAR_H, vertical=True)
        for i, diff in enumerate(DIFFICULTIES):
            count = len(self.levels_by_difficulty[diff])
            label = f"{diff.upper()} ({count})"
            active = i == self._active_difficulty_idx
            if active:
                color = TAB_ACTIVE_COLOR
                shadow = OLIVE_DARK
                text = (255, 255, 255)
            else:
                color = TAB_INACTIVE_COLOR
                shadow = MUTED_COLOR
                text = TEXT_COLOR
            self._tab_buttons.append(
                Button(
                    pygame.Rect(i * tab_w, 0, tab_w, tab_h),
                    label,
                    Action.NOOP,
                    font=self._font_normal,
                    color=color,
                    shadow_color=shadow,
                    text_color=text,
                )
            )

    def _build_action_buttons(self) -> None:
        btn_w = self._scaled(180)
        btn_h = self._scaled(36, vertical=True)
        bar_h = self._scaled(ACTIONS_BAR_H, vertical=True)
        y = self.screen_h - bar_h + (bar_h - btn_h) // 2
        margin = self._scaled(20)
        self._action_buttons = [
            Button(
                pygame.Rect(margin, y, btn_w, btn_h),
                "RETOUR",
                Action.BACK_MENU,
                font=self._font_normal,
                variant="quit",
            ),
            Button(
                pygame.Rect(self.screen_w - margin - btn_w, y, btn_w, btn_h),
                MODE_LAUNCH_LABELS[self.mode],
                Action.PLAY,
                font=self._font_normal,
                variant="primary",
            ),
        ]

    # -------- events --------

    def handle_events(self) -> None:
        result = poll_events(self._action_buttons, audio=self.audio)

        grid_rect = self._grid_panel_rect()

        # Gestion clics onglets : on inspecte les clics bruts pour router par index
        # plutot que via l'enum Action (un onglet = un bouton avec meme Action).
        for cx, cy in list(result.clicks):
            # Onglets
            handled = False
            for i, btn in enumerate(self._tab_buttons):
                if btn.rect.collidepoint(cx, cy):
                    self._set_active_tab(i)
                    self.audio.play_sfx("button")
                    handled = True
                    break
            if handled:
                continue

            # Grille : clic sur une cellule selectionne / double-clic lance.
            # On ignore les clics hors viewport (cellules scrollees hors ecran).
            if not grid_rect.collidepoint(cx, cy):
                continue
            for i, rect in enumerate(self._cell_rects):
                if rect.collidepoint(cx, cy):
                    now = pygame.time.get_ticks()
                    current_diff = DIFFICULTIES[self._active_difficulty_idx]
                    if self._selected_in_tab[current_diff] == i and self._last_click_idx == i \
                            and now - self._last_click_time < 400:
                        self._start_level()
                    else:
                        self._selected_in_tab[current_diff] = i
                    self._last_click_time = now
                    self._last_click_idx = i
                    break

        for action in result:
            if action in (Action.QUIT, Action.BACK_MENU):
                self._back_to_menu()
                return
            if action == Action.PLAY:
                self._start_level()
            elif action == Action.MOVE_LEFT:
                self._set_active_tab((self._active_difficulty_idx - 1) % len(DIFFICULTIES))
            elif action == Action.MOVE_RIGHT:
                self._set_active_tab((self._active_difficulty_idx + 1) % len(DIFFICULTIES))
            elif action == Action.MOVE_UP:
                self._move_selection(-GRID_COLS)
            elif action == Action.MOVE_DOWN:
                self._move_selection(GRID_COLS)
            elif action == Action.SCROLL_UP:
                self._scroll_by(-self._scroll_step())
            elif action == Action.SCROLL_DOWN:
                self._scroll_by(self._scroll_step())

    def _set_active_tab(self, idx: int) -> None:
        self._active_difficulty_idx = idx
        self._scroll_offset = 0
        self._build_tab_buttons()

    def _move_selection(self, delta: int) -> None:
        diff = DIFFICULTIES[self._active_difficulty_idx]
        levels = self.levels_by_difficulty[diff]
        if not levels:
            return
        current = self._selected_in_tab[diff]
        new = max(0, min(len(levels) - 1, current + delta))
        self._selected_in_tab[diff] = new
        self._ensure_selection_visible()

    def _grid_panel_rect(self) -> pygame.Rect:
        tab_h = self._scaled(TAB_BAR_H, vertical=True)
        bar_h = self._scaled(ACTIONS_BAR_H, vertical=True)
        panel_w = self._scaled(GRID_PANEL_W)
        return pygame.Rect(0, tab_h, panel_w, self.screen_h - tab_h - bar_h)

    def _cell_height(self) -> int:
        thumb_h = self._scaled(THUMB_H, vertical=True)
        return thumb_h + self._scaled(CELL_PAD_Y + 16, vertical=True)

    def _content_height(self, levels: list[LevelMeta]) -> int:
        if not levels:
            return 0
        rows = (len(levels) + GRID_COLS - 1) // GRID_COLS
        top_pad = self._scaled(12, vertical=True)
        return top_pad + rows * self._cell_height()

    def _max_scroll(self) -> int:
        diff = DIFFICULTIES[self._active_difficulty_idx]
        levels = self.levels_by_difficulty[diff]
        panel_h = self._grid_panel_rect().height
        return max(0, self._content_height(levels) - panel_h)

    def _scroll_step(self) -> int:
        return self._cell_height()

    def _scroll_by(self, delta: int) -> None:
        self._scroll_offset = max(0, min(self._max_scroll(), self._scroll_offset + delta))

    def _ensure_selection_visible(self) -> None:
        """Ajuste _scroll_offset pour garder la cellule selectionnee visible."""
        diff = DIFFICULTIES[self._active_difficulty_idx]
        levels = self.levels_by_difficulty[diff]
        if not levels:
            return
        idx = self._selected_in_tab[diff]
        row = idx // GRID_COLS
        cell_h = self._cell_height()
        top_pad = self._scaled(12, vertical=True)
        cell_top = top_pad + row * cell_h
        cell_bottom = cell_top + cell_h
        panel_h = self._grid_panel_rect().height

        if cell_top < self._scroll_offset:
            self._scroll_offset = cell_top
        elif cell_bottom > self._scroll_offset + panel_h:
            self._scroll_offset = cell_bottom - panel_h
        self._scroll_offset = max(0, min(self._max_scroll(), self._scroll_offset))

    def _selected_level(self) -> LevelMeta | None:
        diff = DIFFICULTIES[self._active_difficulty_idx]
        levels = self.levels_by_difficulty[diff]
        if not levels:
            return None
        idx = self._selected_in_tab[diff]
        return levels[min(idx, len(levels) - 1)]

    def _start_level(self) -> None:
        lvl = self._selected_level()
        if lvl is None:
            return
        if self.mode == Mode.PLAY:
            from ui.scenes.game import GameScene
            self.manager.switch(
                GameScene(
                    self.manager, lvl, self.audio,
                    screen_w=self.screen_w, screen_h=self.screen_h,
                )
            )
        elif self.mode == Mode.SOLVE:
            from ui.scenes.solver import SolverScene
            self.manager.switch(
                SolverScene(
                    self.manager, lvl, audio=self.audio,
                    screen_w=self.screen_w, screen_h=self.screen_h,
                )
            )
        elif self.mode == Mode.RACE:
            from ui.scenes.race import RaceScene
            self.manager.switch(
                RaceScene(
                    self.manager, lvl, audio=self.audio,
                    screen_w=self.screen_w, screen_h=self.screen_h,
                )
            )

    def _back_to_menu(self) -> None:
        from ui.scenes.menu import MenuScene
        self.manager.switch(
            MenuScene(
                self.manager, audio=self.audio,
                screen_w=self.screen_w, screen_h=self.screen_h,
            )
        )

    def update(self) -> None:
        pass

    # -------- draw --------

    def draw(self, screen: pygame.Surface) -> None:
        assert self._font_title is not None
        assert self._font_normal is not None
        assert self._font_small is not None

        screen.fill(BG_COLOR)

        self._draw_tabs(screen)
        self._draw_grid(screen)
        self._draw_preview(screen)
        self._draw_actions(screen)

    def _draw_tabs(self, screen: pygame.Surface) -> None:
        for btn in self._tab_buttons:
            btn.draw(screen)
        # Souligne l'onglet actif.
        active = self._tab_buttons[self._active_difficulty_idx]
        pygame.draw.rect(screen, HIGHLIGHT_BORDER, active.rect, width=2)

    def _draw_grid(self, screen: pygame.Surface) -> None:
        diff = DIFFICULTIES[self._active_difficulty_idx]
        levels = self.levels_by_difficulty[diff]
        selected_idx = self._selected_in_tab[diff]

        panel_rect = self._grid_panel_rect()
        pygame.draw.rect(screen, PANEL_COLOR, panel_rect)

        self._cell_rects = []
        if not levels:
            msg = self._font_normal.render(
                f"Aucun niveau {diff}.", True, MUTED_COLOR
            )
            screen.blit(
                msg,
                (panel_rect.centerx - msg.get_width() // 2,
                 panel_rect.centery - msg.get_height() // 2),
            )
            return

        # Clamp scroll au cas ou la geometrie a change (resize).
        self._scroll_offset = max(0, min(self._max_scroll(), self._scroll_offset))

        thumb_w = self._scaled(THUMB_W)
        thumb_h = self._scaled(THUMB_H, vertical=True)
        cell_w = thumb_w + self._scaled(CELL_PAD_X)
        cell_h = self._cell_height()
        origin_x = self._scaled(GRID_X_ORIGIN)
        origin_y = panel_rect.top + self._scaled(12, vertical=True)
        label_h = self._scaled(20, vertical=True)

        prev_clip = screen.get_clip()
        screen.set_clip(panel_rect)

        for i, lvl in enumerate(levels):
            col = i % GRID_COLS
            row = i // GRID_COLS
            cx = origin_x + col * cell_w
            cy = origin_y + row * cell_h - self._scroll_offset
            cell_rect = pygame.Rect(cx, cy, thumb_w, thumb_h + label_h)
            self._cell_rects.append(cell_rect)

            # Skip cellules entierement hors viewport.
            if cell_rect.bottom < panel_rect.top or cell_rect.top > panel_rect.bottom:
                continue

            # Vignette.
            thumb = self._thumbnails.get(lvl.name)
            if thumb is not None:
                if thumb.get_size() != (thumb_w, thumb_h):
                    thumb = pygame.transform.scale(thumb, (thumb_w, thumb_h))
                screen.blit(thumb, (cx, cy))
            else:
                pygame.draw.rect(screen, SEPARATOR, (cx, cy, thumb_w, thumb_h))

            if lvl.name in self._completed:
                mark_surf = self._font_small.render("[OK]", True, COMPLETED_MARK_COLOR)
                screen.blit(mark_surf, (cx + thumb_w - mark_surf.get_width() - 4, cy + 4))

            if i == selected_idx:
                pulse = (math.sin(pygame.time.get_ticks() / 400.0) + 1) / 2  # [0, 1]
                border_w = 2 + int(round(2 * pulse))
                halo = pygame.Surface(cell_rect.size, pygame.SRCALPHA)
                halo_alpha = int(40 + 40 * pulse)
                halo.fill((*HIGHLIGHT_BORDER, halo_alpha))
                screen.blit(halo, cell_rect.topleft)
                pygame.draw.rect(screen, HIGHLIGHT_BORDER, cell_rect, width=border_w)

            display_name = lvl.pack if lvl.number is None else f"{lvl.pack} {lvl.number:02d}"
            name_surf = self._font_small.render(display_name, True, TEXT_COLOR)
            screen.blit(
                name_surf,
                (cx + (thumb_w - name_surf.get_width()) // 2, cy + thumb_h + 2),
            )

        screen.set_clip(prev_clip)
        self._draw_scrollbar(screen, panel_rect, levels)

    def _draw_scrollbar(
        self,
        screen: pygame.Surface,
        panel_rect: pygame.Rect,
        levels: list[LevelMeta],
    ) -> None:
        """Dessine une scrollbar passive a droite du panneau grille."""
        content_h = self._content_height(levels)
        if content_h <= panel_rect.height:
            return
        track_w = 6
        track_x = panel_rect.right - track_w - 2
        track_rect = pygame.Rect(track_x, panel_rect.top + 4, track_w, panel_rect.height - 8)
        pygame.draw.rect(screen, CREAM, track_rect, border_radius=3)

        ratio = panel_rect.height / content_h
        thumb_h = max(20, int(track_rect.height * ratio))
        max_scroll = self._max_scroll()
        progress = self._scroll_offset / max_scroll if max_scroll > 0 else 0.0
        thumb_y = track_rect.top + int((track_rect.height - thumb_h) * progress)
        thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_w, thumb_h)
        pygame.draw.rect(screen, HIGHLIGHT_BORDER, thumb_rect, border_radius=3)

    def _draw_preview(self, screen: pygame.Surface) -> None:
        tab_h = self._scaled(TAB_BAR_H, vertical=True)
        bar_h = self._scaled(ACTIONS_BAR_H, vertical=True)
        grid_panel_w = self._scaled(GRID_PANEL_W)
        preview_panel_w = self.screen_w - grid_panel_w
        panel_rect = pygame.Rect(
            grid_panel_w, tab_h,
            preview_panel_w, self.screen_h - tab_h - bar_h,
        )
        pygame.draw.rect(screen, PANEL_COLOR, panel_rect)
        pygame.draw.line(
            screen, SEPARATOR,
            (panel_rect.left, panel_rect.top),
            (panel_rect.left, panel_rect.bottom),
            width=1,
        )

        # Titre du mode (en-tete du panneau preview).
        mode_title = self._font_small.render(
            MODE_TITLES.get(self.mode, ""), True, MUTED_COLOR
        )
        mode_title_y = panel_rect.top + 8
        screen.blit(mode_title, (panel_rect.left + 20, mode_title_y))

        lvl = self._selected_level()
        if lvl is None:
            return

        # Titre niveau -- positionne sous le mode_title reel (le font_small
        # scale avec screen_h donc un offset fixe +28 creait un chevauchement
        # en HD ou la hauteur depasse 20px).
        display_name = lvl.pack if lvl.number is None else f"{lvl.pack} {lvl.number:02d}"
        title = self._font_title.render(display_name, True, TITLE_COLOR)
        title_y = mode_title_y + self._font_small.get_linesize() + 4
        screen.blit(title, (panel_rect.left + 20, title_y))

        # Infos niveau (calculees d'abord pour reserver leur hauteur sous la preview).
        info_lines = [
            f"Difficulte : {lvl.difficulty}",
            f"Caisses    : {lvl.box_count}",
            f"Pack       : {lvl.pack}",
        ]
        completed = lvl.name in self._completed
        if completed:
            info_lines.append("[OK] Deja termine")
            best = self._best.get(lvl.name)
            if best is not None:
                moves, time_s = best
                mins, secs = divmod(int(time_s), 60)
                info_lines.append(f"Meilleur : {moves} coups / {mins:02d}:{secs:02d}")
        else:
            info_lines.append("Jamais termine")

        info_line_h = self._font_small.get_linesize() + 2
        info_block_h = len(info_lines) * info_line_h

        # Apercu : remplit l'espace entre titre et bloc infos (elimine le vide
        # en bas du panneau quand le niveau ne remplissait pas les 200px fixes).
        preview_w = panel_rect.width - 40
        preview_y = title_y + self._font_title.get_linesize() + 8
        bottom_padding = 20
        preview_h = max(
            100,
            panel_rect.bottom - preview_y - info_block_h - 20 - bottom_padding,
        )
        preview_surf = _render_thumbnail(lvl.path, preview_w, preview_h)
        screen.blit(
            preview_surf,
            (
                panel_rect.left + (panel_rect.width - preview_surf.get_width()) // 2,
                preview_y,
            ),
        )

        info_y = preview_y + preview_h + 20
        for line in info_lines:
            if line.startswith("[OK]"):
                color = COMPLETED_MARK_COLOR
            elif line == "Jamais termine":
                color = PENDING_STATUS_COLOR
            else:
                color = TEXT_COLOR
            surf = self._font_small.render(line, True, color)
            screen.blit(surf, (panel_rect.left + 20, info_y))
            info_y += info_line_h

    def _draw_actions(self, screen: pygame.Surface) -> None:
        bar_h = self._scaled(ACTIONS_BAR_H, vertical=True)
        bar_rect = pygame.Rect(0, self.screen_h - bar_h, self.screen_w, bar_h)
        pygame.draw.rect(screen, PANEL_COLOR, bar_rect)

        assert self._font_small is not None
        hint_surf = self._font_small.render(
            "Astuce : double-clic sur un niveau pour le lancer",
            True,
            MUTED_COLOR,
        )
        screen.blit(
            hint_surf,
            (bar_rect.centerx - hint_surf.get_width() // 2, bar_rect.top + 4),
        )

        for btn in self._action_buttons:
            btn.draw(screen)


@lru_cache(maxsize=64)
def _render_thumbnail(path: Path, width: int, height: int) -> pygame.Surface:
    """Rend une vignette d'un niveau tenant dans (width, height).

    Cache LRU par (path, width, height) pour eviter le recalcul.
    """
    board = load_level(path)
    state = board.state
    tile = max(4, min(width // max(state.width, 1), height // max(state.height, 1)))
    renderer = Renderer(tile_size=tile)
    return renderer.render(state)
