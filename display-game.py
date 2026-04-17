"""Construction de l'interface graphique Pygame.

Facade exigee par le sujet. Re-exporte les classes UI du module ui.
"""

from ui.metrics_panel import MetricsPanel
from ui.renderer import Renderer

__all__ = ["MetricsPanel", "Renderer"]


def demo() -> None:
    """Affiche un Board de demonstration dans une fenetre Pygame."""
    from pathlib import Path

    import pygame

    from game.board import Board

    pygame.init()

    board = Board.from_xsb(
        "######\n#    #\n# @$ #\n#  . #\n#    #\n######"
    )
    assets_dir = Path(__file__).resolve().parent / "assets"
    renderer = Renderer(tile_size=64, assets_dir=str(assets_dir))
    surface = renderer.render(board.state)

    screen = pygame.display.set_mode(surface.get_size())
    pygame.display.set_caption("Auto-Sokoban - Demo")
    screen.blit(surface, (0, 0))
    pygame.display.flip()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

    pygame.quit()
