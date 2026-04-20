"""Rendu Pygame de la grille Sokoban avec sprites."""

from __future__ import annotations

from pathlib import Path

import pygame

from game.board import BoardState, detect_corner_deadlocks

# Couleurs de fallback si pas de sprite
FALLBACK_COLORS = {
    "wall": (80, 80, 80),
    "floor": (200, 190, 170),
    "target": (255, 200, 100),
    "box": (160, 100, 40),
    "box_on_target": (100, 200, 100),
    "player": (50, 120, 200),
}


class Renderer:
    """Dessine un BoardState dans une Surface Pygame."""

    _DEFAULT_ASSETS = Path(__file__).resolve().parent.parent / "assets"
    MIN_TILE_SIZE = 1
    MAX_TILE_SIZE = 1024  # ← Limite raisonnable
    MAX_SURFACE_DIM = 8192  # ← 64 Mpixels max

    def __init__(
        self,
        tile_size: int = 64,
        assets_dir: str | Path | None = None,
        variant: int = 0,
    ) -> None:
        if not isinstance(tile_size, int):
            raise ValueError(f"tile_size must be int, got {type(tile_size).__name__}")
        if tile_size < self.MIN_TILE_SIZE or tile_size > self.MAX_TILE_SIZE:
            raise ValueError(f"tile_size must be {self.MIN_TILE_SIZE}-{self.MAX_TILE_SIZE}, got {tile_size}")
        self.tile_size = tile_size
        self._assets_dir = Path(assets_dir) if assets_dir is not None else self._DEFAULT_ASSETS
        self._variant = variant
        self._sprites: dict[str, pygame.Surface] = {}
        self._loaded = False

    def _load_sprites(self) -> None:
        """Charge les sprites depuis assets/. Fallback couleur si absent."""
        if self._loaded:
            return
        self._loaded = True

        mapping = {
            "wall": "tiles/tile_wall.png",
            "floor": "tiles/tile_floor.png",
        }

        # Charger tiles de base
        for key, rel_path in mapping.items():
            full = self._assets_dir / rel_path
            if full.exists():
                img = pygame.image.load(str(full)).convert_alpha()
                self._sprites[key] = pygame.transform.scale(
                    img, (self.tile_size, self.tile_size)
                )

        # Sprite par variante dans chaque sous-dossier
        for key, subdir in [("box", "boxes"), ("target", "targets")]:
            d = self._assets_dir / subdir
            if d.is_dir():
                pngs = sorted(d.glob("*.png"))
                if pngs:
                    idx = self._variant % len(pngs)
                    img = pygame.image.load(str(pngs[idx])).convert_alpha()
                    self._sprites[key] = pygame.transform.scale(
                        img, (self.tile_size, self.tile_size)
                    )

        # Composite box_on_target : box avec teinte verte
        if "box" in self._sprites:
            base = self._sprites["box"].copy()
            overlay = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)
            overlay.fill((0, 180, 0, 60))
            base.blit(overlay, (0, 0))
            pygame.draw.rect(
                base, (0, 200, 0),
                (0, 0, self.tile_size, self.tile_size), width=3,
            )
            self._sprites["box_on_target"] = base

        # Joueur par variante (east + west)
        players_dir = self._assets_dir / "players"
        if players_dir.is_dir():
            player_dirs = sorted(d for d in players_dir.iterdir() if d.is_dir())
            if player_dirs:
                chosen = player_dirs[self._variant % len(player_dirs)]
                for direction_name in ("east", "west"):
                    sprite_path = chosen / f"{direction_name}.png"
                    if sprite_path.exists():
                        img = pygame.image.load(str(sprite_path)).convert_alpha()
                        key = "player" if direction_name == "east" else "player_west"
                        self._sprites[key] = pygame.transform.scale(
                            img, (self.tile_size, self.tile_size)
                        )

    def _draw_tile(self, surface: pygame.Surface, key: str, x: int, y: int) -> None:
        """Dessine un sprite ou un carre de couleur de fallback."""
        if key in self._sprites:
            surface.blit(self._sprites[key], (x, y))
        elif key in FALLBACK_COLORS:
            pygame.draw.rect(
                surface, FALLBACK_COLORS[key],
                (x + 2, y + 2, self.tile_size - 4, self.tile_size - 4),
            )

    def render(self, state: BoardState, facing_left: bool = False) -> pygame.Surface:
        """Retourne une Surface avec le plateau dessine.

        facing_left : si True, utilise le sprite west du joueur.
        """
        self._load_sprites()

        w = state.width * self.tile_size
        h = state.height * self.tile_size
        # Vérifier dimensions finales MAIS avec un peu de tolérance
        if w > self.MAX_SURFACE_DIM or h > self.MAX_SURFACE_DIM:
            raise ValueError(
                f"Rendered surface too large: {w}x{h} (max {self.MAX_SURFACE_DIM}). "
                f"Try reducing tile_size from {self.tile_size} or level size."
            )
        surface = pygame.Surface((w, h))
        surface.fill((0, 0, 0))

        player_key = "player_west" if facing_left and "player_west" in self._sprites else "player"

        for row in range(state.height):
            for col in range(state.width):
                x = col * self.tile_size
                y = row * self.tile_size
                pos = (row, col)

                if pos in state.walls:
                    self._draw_tile(surface, "wall", x, y)
                    continue

                # Sol en fond
                self._draw_tile(surface, "floor", x, y)

                # Superpositions
                if pos in state.targets:
                    self._draw_tile(surface, "target", x, y)

                if pos in state.boxes:
                    if pos in state.targets:
                        self._draw_tile(surface, "box_on_target", x, y)
                    else:
                        self._draw_tile(surface, "box", x, y)

                if pos == state.player:
                    self._draw_tile(surface, player_key, x, y)

        return surface

    def render_heatmap_overlay(
        self, state: BoardState, visit_counts: dict[tuple[int, int], int],
    ) -> pygame.Surface:
        """Retourne un overlay semi-transparent avec gradient bleu->rouge par case."""
        w = state.width * self.tile_size
        h = state.height * self.tile_size
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)

        if not visit_counts:
            return overlay

        # ✅ CORRECTION : Filtrer les positions invalides plutôt que de lever une erreur
        valid_counts = {
            (row, col): count
            for (row, col), count in visit_counts.items()
            if 0 <= row < state.height and 0 <= col < state.width
        }
        
        if not valid_counts:
            return overlay

        max_count = max(valid_counts.values())
        if max_count == 0:
            return overlay

        # Utiliser valid_counts au lieu de visit_counts
        for (row, col), count in valid_counts.items():
            if (row, col) in state.walls:
                continue
            t = count / max_count
            r = int(50 + 180 * t)
            g = int(50 - 20 * t)
            b = int(200 - 170 * t)
            alpha = int(50 + 130 * t)
            x = col * self.tile_size
            y = row * self.tile_size
            pygame.draw.rect(overlay, (r, g, b, alpha), (x, y, self.tile_size, self.tile_size))

        return overlay

    def render_deadlock_overlay(self, state: BoardState) -> pygame.Surface:
        """Retourne un overlay rouge semi-transparent sur les caisses en deadlock coin."""
        w = state.width * self.tile_size
        h = state.height * self.tile_size
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)

        deadlocks = detect_corner_deadlocks(state)
        if not deadlocks:
            return overlay

        ts = self.tile_size
        for row, col in deadlocks:
            x = col * ts
            y = row * ts
            pygame.draw.rect(overlay, (220, 40, 40, 100), (x, y, ts, ts))
            margin = ts // 4
            pygame.draw.line(
                overlay, (255, 60, 60, 200),
                (x + margin, y + margin), (x + ts - margin, y + ts - margin), 3,
            )
            pygame.draw.line(
                overlay, (255, 60, 60, 200),
                (x + ts - margin, y + margin), (x + margin, y + ts - margin), 3,
            )

        return overlay
