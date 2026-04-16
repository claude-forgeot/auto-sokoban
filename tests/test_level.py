"""Tests unitaires pour game/level.py."""

import pytest

from game.level import list_levels, load_level

LEVEL_SIMPLE = """\
####
#  #
#$ #
# .#
# @#
####"""

LEVEL_INVALID = """\
####
#$ #
####"""


class TestLoadLevel:
    def test_load_valid(self, tmp_path):
        f = tmp_path / "test.xsb"
        f.write_text(LEVEL_SIMPLE)
        board = load_level(f)
        assert board.state.player == (4, 2)
        assert not board.is_won()

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_level("/inexistant/niveau.xsb")

    def test_load_invalid_content(self, tmp_path):
        f = tmp_path / "bad.xsb"
        f.write_text(LEVEL_INVALID)
        with pytest.raises(ValueError):
            load_level(f)


class TestListLevels:
    def test_list_empty_dir(self, tmp_path):
        assert list_levels(tmp_path) == []

    def test_list_nonexistent_dir(self):
        assert list_levels("/dossier/inexistant") == []

    def test_list_with_levels(self, tmp_path):
        (tmp_path / "easy.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        assert len(levels) == 1
        assert levels[0].name == "easy"
        assert levels[0].box_count == 1
        assert levels[0].difficulty == "facile"

    def test_list_skips_invalid(self, tmp_path):
        (tmp_path / "good.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "bad.xsb").write_text(LEVEL_INVALID)
        levels = list_levels(tmp_path)
        assert len(levels) == 1
        assert levels[0].name == "good"

    def test_list_sorted_by_name(self, tmp_path):
        (tmp_path / "b_level.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "a_level.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        assert [l.name for l in levels] == ["a_level", "b_level"]

    def test_difficulty_medium(self, tmp_path):
        # 4 caisses = moyen
        level = """\
########
#      #
# $$$$ #
# .... #
#  @   #
########"""
        (tmp_path / "medium.xsb").write_text(level)
        levels = list_levels(tmp_path)
        assert levels[0].difficulty == "moyen"
        assert levels[0].box_count == 4

    def test_difficulty_hard(self, tmp_path):
        # 6 caisses = difficile
        level = """\
##########
#        #
# $$$$$$ #
# ...... #
#   @    #
##########"""
        (tmp_path / "hard.xsb").write_text(level)
        levels = list_levels(tmp_path)
        assert levels[0].difficulty == "difficile"
        assert levels[0].box_count == 6
