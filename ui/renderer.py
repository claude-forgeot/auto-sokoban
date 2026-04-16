"""Rendu Pygame de la grille Sokoban avec sprites."""

from __future__ import annotations

from pathlib import Path

import pygame

from game.board import BoardState

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

    def __init__(
        self,
        tile_size: int = 64,
        assets_dir: str | Path = "assets",
    ) -> None:
        self.tile_size = tile_size
        self._assets_dir = Path(assets_dir)
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

        # Premier sprite trouve dans chaque sous-dossier
        for key, subdir in [("box", "boxes"), ("target", "targets")]:
            d = self._assets_dir / subdir
            if d.is_dir():
                pngs = sorted(d.glob("*.png"))
                if pngs:
                    img = pygame.image.load(str(pngs[0])).convert_alpha()
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

        # Premier joueur trouve
        players_dir = self._assets_dir / "players"
        if players_dir.is_dir():
            for subdir in sorted(players_dir.iterdir()):
                if subdir.is_dir():
                    east = subdir / "east.png"
                    if east.exists():
                        img = pygame.image.load(str(east)).convert_alpha()
                        self._sprites["player"] = pygame.transform.scale(
                            img, (self.tile_size, self.tile_size)
                        )
                        break

    def _draw_tile(self, surface: pygame.Surface, key: str, x: int, y: int) -> None:
        """Dessine un sprite ou un carre de couleur de fallback."""
        if key in self._sprites:
            surface.blit(self._sprites[key], (x, y))
        elif key in FALLBACK_COLORS:
            pygame.draw.rect(
                surface, FALLBACK_COLORS[key],
                (x + 2, y + 2, self.tile_size - 4, self.tile_size - 4),
            )

    def render(self, state: BoardState) -> pygame.Surface:
        """Retourne une Surface avec le plateau dessine."""
        self._load_sprites()

        w = state.width * self.tile_size
        h = state.height * self.tile_size
        surface = pygame.Surface((w, h))
        surface.fill((0, 0, 0))

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
                    self._draw_tile(surface, "player", x, y)

        return surface
