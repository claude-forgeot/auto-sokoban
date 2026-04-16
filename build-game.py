"""Construction de la logique de jeu Sokoban (matrice, regles, etat).

Facade exigee par le sujet. Re-exporte les classes et fonctions du module game.
"""

from game.board import Board, BoardState, Direction
from game.level import LevelMeta, list_levels, load_level

__all__ = [
    "Board",
    "BoardState",
    "Direction",
    "LevelMeta",
    "list_levels",
    "load_level",
]


def demo() -> Board:
    """Cree un Board de test pour verification rapide."""
    xsb = """\
####
#  #
#$ #
# .#
# @#
####"""
    return Board.from_xsb(xsb)
