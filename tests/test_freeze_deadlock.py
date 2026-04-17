"""Tests pour detect_freeze_deadlocks et is_lost (game/board.py)."""

from game.board import Board, detect_freeze_deadlocks, is_lost


def _state(xsb: str):
    """Helper : construit un BoardState depuis un snippet XSB."""
    return Board.from_xsb(xsb).state


class TestFreezeDeadlockBasics:
    def test_no_freeze_when_open(self):
        # 1 caisse, 1 cible, aucune contrainte murale proche.
        state = _state(
            """\
######
#    #
# $  #
#  . #
# @  #
######"""
        )
        assert detect_freeze_deadlocks(state) == set()
        assert not is_lost(state)

    def test_corner_is_frozen(self):
        # 1 caisse dans coin mur-mur + 1 cible plus loin.
        state = _state(
            """\
######
#$   #
#    #
#.  @#
######"""
        )
        frozen = detect_freeze_deadlocks(state)
        assert (1, 1) in frozen
        assert is_lost(state)

    def test_single_wall_side_not_frozen_alone(self):
        # 1 caisse contre UN SEUL mur (frozen_y vrai mais frozen_x faux).
        state = _state(
            """\
######
# $  #
#    #
#.  @#
######"""
        )
        # (1,2) : up wall, down empty -> frozen_y true. left empty, right empty -> frozen_x false.
        # Donc pas frozen.
        assert detect_freeze_deadlocks(state) == set()
        assert not is_lost(state)


class TestFreezeDeadlockL:
    def test_two_boxes_L_against_wall(self):
        # 2 caisses en L : une contre mur-haut + mur-gauche, l'autre contre
        # caisse frozen + mur-gauche. 2 caisses, 2 cibles.
        state = _state(
            """\
######
#$   #
#$   #
#@.. #
######"""
        )
        # (1,1) : up wall, left wall -> frozen.
        # (2,1) : left wall, up = caisse (1,1) frozen -> blocked. frozen_y true.
        #         frozen_x : left wall -> true. frozen.
        frozen = detect_freeze_deadlocks(state)
        assert (1, 1) in frozen
        assert (2, 1) in frozen
        assert is_lost(state)


class TestFreezeDeadlockSquare:
    def test_four_boxes_square_floating_is_frozen(self):
        # Carre 2x2 au milieu : chaque caisse bloque ses voisines via recursion.
        # Aucune caisse ne peut bouger. 4 caisses, 4 cibles.
        state = _state(
            """\
######
#    #
# $$ #
# $$ #
#....#
#   @#
######"""
        )
        frozen = detect_freeze_deadlocks(state)
        assert (2, 2) in frozen
        assert (2, 3) in frozen
        assert (3, 2) in frozen
        assert (3, 3) in frozen
        assert is_lost(state)

    def test_four_boxes_square_against_wall(self):
        # Carre 2x2 colle au coin haut-gauche. 4 caisses, 4 cibles.
        state = _state(
            """\
######
#$$  #
#$$  #
#....#
#  @ #
######"""
        )
        frozen = detect_freeze_deadlocks(state)
        assert (1, 1) in frozen
        assert (1, 2) in frozen
        assert (2, 1) in frozen
        assert (2, 2) in frozen
        assert is_lost(state)


class TestFreezeDeadlockCascade:
    def test_cascade_box_blocked_by_box_blocked_by_wall(self):
        # Cascade verticale : 3 caisses alignees contre mur haut + mur gauche.
        # 3 caisses, 3 cibles.
        state = _state(
            """\
######
#$   #
#$   #
#$   #
#@...#
######"""
        )
        # (1,1) : up wall, left wall -> frozen.
        # (2,1) : left wall, up (1,1) frozen -> blocked. frozen.
        # (3,1) : left wall, up (2,1) frozen -> blocked. frozen.
        frozen = detect_freeze_deadlocks(state)
        assert (1, 1) in frozen
        assert (2, 1) in frozen
        assert (3, 1) in frozen
        assert is_lost(state)


class TestFreezeDeadlockOnGoal:
    def test_not_lost_when_only_frozen_on_target(self):
        # 1 caisse sur cible (donc won), pas de deadlock malgre coin.
        state = _state(
            """\
#####
# * #
# @ #
#####"""
        )
        assert state.is_won()
        assert not is_lost(state)

    def test_lost_ignores_frozen_on_target_but_detects_off_target(self):
        # 2 caisses : une frozen sur cible (OK), une frozen hors cible (KO).
        # 2 cibles.
        state = _state(
            """\
#######
#*    #
#     #
#$.  @#
#######"""
        )
        # '*' a (1,1) = box+target. '$' a (3,1) = box. '.' a (3,2) = target.
        # (1,1) frozen (coin mur haut+mur gauche) mais SUR cible -> ignoree.
        # (3,1) frozen (coin mur gauche+mur bas) HORS cible -> is_lost True.
        frozen = detect_freeze_deadlocks(state)
        assert (1, 1) in frozen
        assert (3, 1) in frozen
        assert is_lost(state)

    def test_not_lost_when_all_frozen_are_on_targets(self):
        # Toutes les caisses frozen sont sur cible : niveau won.
        state = _state(
            """\
######
#*  *#
#    #
#   @#
######"""
        )
        assert state.is_won()
        assert not is_lost(state)
