"""Point d'entree du jeu Auto-Sokoban."""

import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)

# Centrer la fenetre au lancement plutot que laisser le WM (GNOME/tiling)
# la placer/maximiser automatiquement. Doit etre defini avant pygame.init().
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

import pygame

from ui.audio import AudioManager
from ui.layout import BASE_H, BASE_W, clamp_window_size
from ui.scenes.base import SceneManager
from ui.scenes.menu import MenuScene

FPS = 30


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((BASE_W, BASE_H), pygame.RESIZABLE)
    pygame.display.set_caption("Auto-Sokoban")
    clock = pygame.time.Clock()

    audio = AudioManager()
    audio.load()

    manager = SceneManager()
    menu = MenuScene(manager, audio=audio, screen_w=BASE_W, screen_h=BASE_H)
    manager.switch(menu)

    current_w, current_h = BASE_W, BASE_H

    while manager.running:
        # Ecoute brute VIDEORESIZE au niveau main (poll_events est aussi appele
        # par chaque scene, mais un resize pre-scene garantit que la surface
        # est a jour avant le prochain draw).
        for event in pygame.event.get(pygame.VIDEORESIZE):
            new_w, new_h = clamp_window_size(event.w, event.h)
            if (new_w, new_h) != (current_w, current_h):
                current_w, current_h = new_w, new_h
                screen = pygame.display.set_mode(
                    (current_w, current_h), pygame.RESIZABLE
                )
                if manager.scene is not None:
                    manager.scene.on_resize(current_w, current_h)

        if manager.scene is not None:
            manager.scene.handle_events()
            manager.scene.update()
            manager.scene.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
