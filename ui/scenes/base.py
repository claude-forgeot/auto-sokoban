"""Classe de base pour les scenes et gestionnaire de scenes."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pygame


class Scene(ABC):
    """Scene de base. Chaque scene gere ses propres evenements et rendu."""

    def __init__(self, manager: SceneManager) -> None:
        self.manager = manager

    @abstractmethod
    def handle_events(self) -> None:
        """Traite les evenements Pygame."""
        ...

    @abstractmethod
    def update(self) -> None:
        """Met a jour la logique de la scene."""
        ...

    @abstractmethod
    def draw(self, screen: pygame.Surface) -> None:
        """Dessine la scene."""
        ...

    def on_enter(self) -> None:
        """Appele quand la scene devient active."""

    def on_exit(self) -> None:
        """Appele quand la scene est remplacee."""

    def on_resize(self, new_w: int, new_h: int) -> None:
        """Appele lors d'un redimensionnement de fenetre. Override si besoin."""


class SceneManager:
    """Gere la scene active et les transitions."""

    def __init__(self) -> None:
        self._scene: Scene | None = None
        self.running = True

    @property
    def scene(self) -> Scene | None:
        return self._scene

    def switch(self, scene: Scene) -> None:
        """Change de scene avec fondu noir 150ms (skip au premier demarrage)."""
        old = self._scene
        screen = pygame.display.get_surface()

        if old is not None and screen is not None:
            old_snapshot = screen.copy()
            old.on_exit()
        else:
            old_snapshot = None

        self._scene = scene
        scene.on_enter()

        if old_snapshot is not None and screen is not None:
            new_snapshot = screen.copy()
            scene.draw(new_snapshot)
            self._fade_transition(screen, old_snapshot, new_snapshot)

    @staticmethod
    def _fade_transition(
        screen: pygame.Surface,
        old_snapshot: pygame.Surface,
        new_snapshot: pygame.Surface,
    ) -> None:
        FRAMES = 9
        overlay = pygame.Surface(screen.get_size())
        overlay.fill((0, 0, 0))
        clock = pygame.time.Clock()
        for i in range(FRAMES):
            t = i / (FRAMES - 1)
            if t < 0.5:
                screen.blit(old_snapshot, (0, 0))
                alpha = int(255 * 2 * t)
            else:
                screen.blit(new_snapshot, (0, 0))
                alpha = int(255 * (1 - 2 * (t - 0.5)))
            overlay.set_alpha(alpha)
            screen.blit(overlay, (0, 0))
            pygame.display.flip()
            clock.tick(60)

    def quit(self) -> None:
        self.running = False
