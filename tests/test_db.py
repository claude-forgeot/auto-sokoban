"""Tests unitaires pour game/db.py."""

import pytest

from game import db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Redirige _DB_PATH vers une BDD temporaire isolee."""
    path = tmp_path / "test_scores.db"
    monkeypatch.setattr(db, "_DB_PATH", path)
    monkeypatch.setattr(db, "_LEGACY_DB_PATH", tmp_path / "nonexistent_legacy.db")
    return path


class TestGetCompletedLevels:
    def test_empty_when_no_scores(self, tmp_db):
        assert db.get_completed_levels() == set()

    def test_returns_distinct_levels(self, tmp_db):
        db.save_score("alice", "easy_1", 10, 5.0)
        db.save_score("bob", "easy_1", 12, 6.0)
        db.save_score("alice", "hard_1", 30, 60.0)
        assert db.get_completed_levels() == {"easy_1", "hard_1"}


class TestGetBestForLevel:
    def test_none_when_level_absent(self, tmp_db):
        assert db.get_best_for_level("inexistant") is None

    def test_none_when_db_empty(self, tmp_db):
        assert db.get_best_for_level("easy_1") is None

    def test_returns_best_record_as_single_row(self, tmp_db):
        """Le meilleur score est une ligne reelle (pas un melange min/min)."""
        db.save_score("alice", "easy_1", 20, 30.0)
        db.save_score("bob", "easy_1", 15, 45.0)
        db.save_score("carol", "easy_1", 18, 25.0)
        best = db.get_best_for_level("easy_1")
        # bob a le moins de coups (15) => sa ligne gagne
        assert best == (15, 45.0)

    def test_tiebreaker_on_time_when_moves_equal(self, tmp_db):
        """A egalite de coups, le temps le plus court gagne."""
        db.save_score("alice", "easy_1", 15, 60.0)
        db.save_score("bob", "easy_1", 15, 30.0)
        assert db.get_best_for_level("easy_1") == (15, 30.0)

    def test_isolated_per_level(self, tmp_db):
        db.save_score("alice", "easy_1", 10, 5.0)
        db.save_score("bob", "hard_1", 50, 120.0)
        assert db.get_best_for_level("easy_1") == (10, 5.0)
        assert db.get_best_for_level("hard_1") == (50, 120.0)

    def test_types_are_int_and_float(self, tmp_db):
        db.save_score("alice", "easy_1", 10, 5.5)
        best = db.get_best_for_level("easy_1")
        assert best is not None
        assert isinstance(best[0], int)
        assert isinstance(best[1], float)
