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
        """Change de scene."""
        if self._scene is not None:
            self._scene.on_exit()
        self._scene = scene
        self._scene.on_enter()

    def quit(self) -> None:
        self.running = False
