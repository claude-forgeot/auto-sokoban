"""Tests unitaires pour game/board.py."""

import pytest

from game.board import Board, Direction

# Niveau de reference pour les tests (Sokoban classique #1 simplifie)
#   ####
#   #  #
#   #$ #
#   # .#
#   # @#
#   ####
LEVEL_SIMPLE = """\
####
#  #
#$ #
# .#
# @#
####"""

# Niveau deja gagne (caisse sur cible)
LEVEL_WON = """\
####
#* #
# @#
####"""

# Niveau avec 2 caisses
LEVEL_TWO_BOXES = """\
######
#    #
# $$ #
# .. #
#  @ #
######"""


class TestDirection:
    def test_deltas(self):
        assert Direction.UP.delta == (-1, 0)
        assert Direction.DOWN.delta == (1, 0)
        assert Direction.LEFT.delta == (0, -1)
        assert Direction.RIGHT.delta == (0, 1)

    def test_iteration(self):
        dirs = list(Direction)
        assert len(dirs) == 4


class TestBoardState:
    def test_is_won_true(self):
        board = Board.from_xsb(LEVEL_WON)
        assert board.state.is_won()

    def test_is_won_false(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        assert not board.state.is_won()

    def test_at(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        s = board.state
        assert s.at((0, 0)) == "wall"
        assert s.at((4, 2)) == "player"
        assert s.at((2, 1)) == "box"
        assert s.at((3, 2)) == "target"
        assert s.at((1, 1)) == "empty"

    def test_hash_same_state(self):
        b1 = Board.from_xsb(LEVEL_SIMPLE)
        b2 = Board.from_xsb(LEVEL_SIMPLE)
        assert hash(b1.state) == hash(b2.state)
        assert b1.state == b2.state

    def test_hash_different_state(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        s1 = board.state
        board.move(Direction.UP)
        s2 = board.state
        assert s1 != s2

    def test_hashable_in_set(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        visited = {board.state}
        assert board.state in visited


class TestBoardMove:
    def test_move_valid(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        assert board.move(Direction.UP)
        assert board.state.player == (3, 2)

    def test_move_blocked_by_wall(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        assert not board.move(Direction.RIGHT)
        assert board.state.player == (4, 2)

    def test_push_box(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        board.move(Direction.UP)  # (4,2) -> (3,2)
        board.move(Direction.UP)  # (3,2) -> (2,2)
        # Le joueur est maintenant a cote de la caisse en (2,1)
        board.move(Direction.LEFT)  # (2,2) -> (2,1), pousse caisse
        # Caisse doit etre poussee de (2,1) vers (2,0)? Non, (2,0) est un mur
        # Reconsiderons le niveau:
        # ####
        # #  #
        # #$ #   <- caisse en (2,1)
        # # .#
        # # @#   <- joueur en (4,2)
        # ####
        # Apres UP: (3,2), apres UP: (2,2)
        # LEFT depuis (2,2): cible (2,1) a une caisse, beyond (2,0) est '#' -> bloque
        assert not board.move(Direction.LEFT)

    def test_push_box_success(self):
        # Niveau ou la poussee reussit
        board = Board.from_xsb(LEVEL_SIMPLE)
        # Joueur en (4,2), caisse en (2,1)
        # Aller a gauche de la caisse : (2,2) puis pousser a gauche ne marche pas (mur)
        # Aller en dessous de la caisse : (3,1) puis pousser vers le haut
        board.move(Direction.LEFT)   # (4,2) -> (4,1)
        board.move(Direction.UP)     # (4,1) -> (3,1)
        board.move(Direction.UP)     # (3,1) -> (2,1) pousse caisse de (2,1) vers (1,1)
        assert board.state.player == (2, 1)
        assert (1, 1) in board.state.boxes
        assert (2, 1) not in board.state.boxes

    def test_push_box_blocked_by_wall(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        board.move(Direction.UP)     # (4,2) -> (3,2)
        board.move(Direction.UP)     # (3,2) -> (2,2)
        # Caisse en (2,1), joueur en (2,2). Pousser caisse vers la gauche (mur en 2,0)
        assert not board.move(Direction.LEFT)

    def test_push_box_blocked_by_box(self):
        board = Board.from_xsb(LEVEL_TWO_BOXES)
        # ######
        # #    #
        # # $$ #    <- caisses en (2,2) et (2,3)
        # # .. #
        # #  @ #
        # ######
        board.move(Direction.UP)     # (4,3) -> (3,3)
        board.move(Direction.UP)     # (3,3) -> (2,3) pousse caisse (2,3) vers (1,3)
        # Maintenant joueur en (2,3), caisse en (2,2) toujours la
        board.move(Direction.LEFT)   # (2,3) -> (2,2) pousse caisse (2,2) vers (2,1)
        # Joueur en (2,2). Caisse en (2,1), mur en (2,0)? Non, (2,0) est un mur '#'
        # Pousser encore a gauche : beyond (2,0) est mur -> bloque
        assert not board.move(Direction.LEFT)


class TestBoardUndo:
    def test_undo(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        initial_player = board.state.player
        board.move(Direction.UP)
        assert board.state.player != initial_player
        assert board.undo()
        assert board.state.player == initial_player

    def test_undo_empty_history(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        assert not board.undo()

    def test_undo_restores_box(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        board.move(Direction.LEFT)   # (4,2) -> (4,1)
        board.move(Direction.UP)     # (4,1) -> (3,1)
        old_boxes = board.state.boxes
        board.move(Direction.UP)     # pousse caisse de (2,1) vers (1,1)
        assert board.state.boxes != old_boxes
        board.undo()
        assert board.state.boxes == old_boxes


class TestBoardReset:
    def test_reset(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        initial = board.state
        board.move(Direction.UP)
        board.move(Direction.UP)
        board.reset()
        assert board.state == initial

    def test_reset_clears_history(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        board.move(Direction.UP)
        board.reset()
        assert not board.undo()


class TestBoardIsWon:
    def test_won_level(self):
        board = Board.from_xsb(LEVEL_WON)
        assert board.is_won()

    def test_not_won(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        assert not board.is_won()

    def test_win_by_pushing(self):
        # Niveau minimal : pousser une caisse sur la cible
        level = """\
####
# .#
# $#
# @#
####"""
        board = Board.from_xsb(level)
        assert not board.is_won()
        board.move(Direction.UP)  # pousse caisse de (2,2) vers (1,2) = cible
        assert board.is_won()


class TestFromXsb:
    def test_basic_parsing(self):
        board = Board.from_xsb(LEVEL_SIMPLE)
        s = board.state
        assert s.player == (4, 2)
        assert (2, 1) in s.boxes
        assert (3, 2) in s.targets
        assert len(s.boxes) == len(s.targets) == 1
        assert s.width == 4
        assert s.height == 6

    def test_box_on_target(self):
        board = Board.from_xsb(LEVEL_WON)
        s = board.state
        # '*' = box + target a la meme position
        assert (1, 1) in s.boxes
        assert (1, 1) in s.targets

    def test_player_on_target(self):
        level = """\
####
#$ #
#+ #
####"""
        board = Board.from_xsb(level)
        s = board.state
        assert s.player == (2, 1)
        assert (2, 1) in s.targets

    def test_no_player_raises(self):
        with pytest.raises(ValueError, match="pas de joueur"):
            Board.from_xsb("####\n#$.#\n####")

    def test_mismatched_boxes_targets_raises(self):
        with pytest.raises(ValueError, match="caisses"):
            Board.from_xsb("####\n#$@#\n####")
