"""Fixtures partagees pour les tests.

Nouveaux tests : preferer ces fixtures plutot que redefinir des
constantes LEVEL_* localement. Les tests existants conservent leurs
constantes locales pour minimiser le risque de regression.
"""

import pytest

from game.board import Board, BoardState

LEVEL_WON_XSB = """\
####
#* #
# @#
####"""

LEVEL_PUSH_UP_XSB = """\
####
# .#
# $#
# @#
####"""

LEVEL_SIMPLE_XSB = """\
######
#    #
# @$ #
#  . #
#    #
######"""


@pytest.fixture
def won_board() -> Board:
    """Niveau deja gagne : une caisse sur cible."""
    return Board.from_xsb(LEVEL_WON_XSB)


@pytest.fixture
def won_state(won_board: Board) -> BoardState:
    return won_board.state


@pytest.fixture
def push_up_board() -> Board:
    """Niveau minimal : pousser une caisse vers le haut (3 coups)."""
    return Board.from_xsb(LEVEL_PUSH_UP_XSB)


@pytest.fixture
def push_up_state(push_up_board: Board) -> BoardState:
    return push_up_board.state


@pytest.fixture
def simple_board() -> Board:
    """Niveau 6x6 avec une caisse a pousser vers une cible."""
    return Board.from_xsb(LEVEL_SIMPLE_XSB)


@pytest.fixture
def simple_state(simple_board: Board) -> BoardState:
    return simple_board.state
