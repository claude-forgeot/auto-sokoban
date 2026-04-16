"""Point d'entree du jeu Auto-Sokoban."""

import pygame

from ui.scenes.base import SceneManager
from ui.scenes.menu import MenuScene

SCREEN_W = 800
SCREEN_H = 600
FPS = 30


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Auto-Sokoban")
    clock = pygame.time.Clock()

    manager = SceneManager()
    menu = MenuScene(manager, screen_w=SCREEN_W, screen_h=SCREEN_H)
    manager.switch(menu)

    while manager.running:
        if manager.scene is not None:
            manager.scene.handle_events()
            manager.scene.update()
            manager.scene.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
