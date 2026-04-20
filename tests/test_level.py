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


@pytest.fixture
def fake_levels_dir(tmp_path, monkeypatch):
    """Reproduit la structure repo (<root>/game/level.py + <root>/levels/) dans tmp_path
    et patche game.level.__file__ pour que la validation de chemin accepte les fichiers
    sous le dossier levels/ temporaire.
    """
    fake_root = tmp_path / "fake_root"
    fake_game = fake_root / "game"
    fake_lvls = fake_root / "levels"
    fake_game.mkdir(parents=True)
    fake_lvls.mkdir(parents=True)
    fake_file = fake_game / "level.py"
    fake_file.touch()
    monkeypatch.setattr("game.level.__file__", str(fake_file))
    return fake_lvls


class TestLoadLevel:
    def test_load_valid(self, fake_levels_dir):
        f = fake_levels_dir / "test.xsb"
        f.write_text(LEVEL_SIMPLE)
        board = load_level(f)
        assert board.state.player == (4, 2)
        assert not board.is_won()

    def test_load_missing_file(self, fake_levels_dir):
        with pytest.raises(FileNotFoundError):
            load_level(fake_levels_dir / "niveau_inexistant.xsb")

    def test_load_invalid_content(self, fake_levels_dir):
        f = fake_levels_dir / "bad.xsb"
        f.write_text(LEVEL_INVALID)
        with pytest.raises(ValueError):
            load_level(f)


class TestListLevelsSubdirs:
    """Structure nouvelle : levels/<difficulte>/<pack>_<num>.xsb."""

    def test_empty_root(self, tmp_path):
        assert list_levels(tmp_path) == []

    def test_nonexistent_dir(self):
        assert list_levels("/dossier/inexistant") == []

    def test_difficulty_from_folder(self, tmp_path):
        (tmp_path / "facile").mkdir()
        (tmp_path / "moyen").mkdir()
        (tmp_path / "difficile").mkdir()
        (tmp_path / "facile" / "tuto_01.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "moyen" / "tuto_01.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "difficile" / "tuto_01.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        assert len(levels) == 3
        by_diff = {l.difficulty: l for l in levels}
        assert set(by_diff) == {"facile", "moyen", "difficile"}

    def test_composite_name_unique(self, tmp_path):
        """Deux fichiers tuto_01.xsb dans des dossiers differents -> names uniques."""
        (tmp_path / "facile").mkdir()
        (tmp_path / "moyen").mkdir()
        (tmp_path / "facile" / "tuto_01.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "moyen" / "tuto_01.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        names = [l.name for l in levels]
        assert "facile/tuto_01" in names
        assert "moyen/tuto_01" in names
        assert len(set(names)) == len(names)

    def test_pack_and_number_parsed(self, tmp_path):
        (tmp_path / "facile").mkdir()
        (tmp_path / "facile" / "tuto_03.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "facile" / "maison_12.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        by_pack = {l.pack: l for l in levels}
        assert by_pack["tuto"].number == 3
        assert by_pack["maison"].number == 12

    def test_sorted_by_difficulty_then_name(self, tmp_path):
        (tmp_path / "facile").mkdir()
        (tmp_path / "difficile").mkdir()
        (tmp_path / "difficile" / "tuto_01.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "facile" / "tuto_02.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "facile" / "tuto_01.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        assert [l.name for l in levels] == [
            "facile/tuto_01",
            "facile/tuto_02",
            "difficile/tuto_01",
        ]

    def test_skips_invalid(self, tmp_path):
        (tmp_path / "facile").mkdir()
        (tmp_path / "facile" / "good.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "facile" / "bad.xsb").write_text(LEVEL_INVALID)
        levels = list_levels(tmp_path)
        assert len(levels) == 1
        assert levels[0].pack == "good"

    def test_number_none_for_nonconforming(self, tmp_path):
        (tmp_path / "facile").mkdir()
        (tmp_path / "facile" / "freeform.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        assert levels[0].pack == "freeform"
        assert levels[0].number is None


class TestListLevelsFlat:
    """Retrocompat : structure a plat avec prefixe de difficulte."""

    def test_flat_easy_prefix(self, tmp_path):
        (tmp_path / "easy_1.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        assert len(levels) == 1
        assert levels[0].difficulty == "facile"
        assert levels[0].name == "easy_1"

    def test_flat_medium_and_hard(self, tmp_path):
        level_medium = """\
########
#      #
# $$$$ #
# .... #
#  @   #
########"""
        level_hard = """\
##########
#        #
# $$$$$$ #
# ...... #
#   @    #
##########"""
        (tmp_path / "medium_1.xsb").write_text(level_medium)
        (tmp_path / "hard_1.xsb").write_text(level_hard)
        levels = list_levels(tmp_path)
        by_diff = {l.difficulty: l for l in levels}
        assert by_diff["moyen"].box_count == 4
        assert by_diff["difficile"].box_count == 6

    def test_flat_difficulty_from_box_count(self, tmp_path):
        (tmp_path / "freeform.xsb").write_text(LEVEL_SIMPLE)
        levels = list_levels(tmp_path)
        assert levels[0].difficulty == "facile"  # 1 caisse -> facile

    def test_flat_skips_invalid(self, tmp_path):
        (tmp_path / "good.xsb").write_text(LEVEL_SIMPLE)
        (tmp_path / "bad.xsb").write_text(LEVEL_INVALID)
        levels = list_levels(tmp_path)
        assert len(levels) == 1
        assert levels[0].name == "good"
