"""Gestion du classement en base de donnees SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "scores.db"


@dataclass(frozen=True)
class ScoreEntry:
    """Une entree du classement."""

    player: str
    level: str
    moves: int
    time_s: float
    date: str


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT NOT NULL,
            level TEXT NOT NULL,
            moves INTEGER NOT NULL,
            time_s REAL NOT NULL,
            date TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )"""
    )
    conn.commit()
    return conn


def save_score(player: str, level: str, moves: int, time_s: float) -> None:
    """Sauvegarde un score dans la base."""
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO scores (player, level, moves, time_s) VALUES (?, ?, ?, ?)",
            (player, level, moves, round(time_s, 1)),
        )
        conn.commit()


def get_ranking(level: str, limit: int = 10) -> list[ScoreEntry]:
    """Retourne le classement pour un niveau, trie par coups puis temps."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT player, level, moves, time_s, date FROM scores "
            "WHERE level = ? ORDER BY moves ASC, time_s ASC LIMIT ?",
            (level, limit),
        ).fetchall()
    return [ScoreEntry(*row) for row in rows]


def get_all_ranking(limit: int = 20) -> list[ScoreEntry]:
    """Retourne le classement global tous niveaux confondus."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT player, level, moves, time_s, date FROM scores "
            "ORDER BY moves ASC, time_s ASC LIMIT ?",
            (limit,),
        ).fetchall()
    return [ScoreEntry(*row) for row in rows]


def get_completed_levels() -> set[str]:
    """Retourne l'ensemble des niveaux avec au moins un score enregistre."""
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT DISTINCT level FROM scores").fetchall()
    return {row[0] for row in rows}


def get_best_for_level(level: str) -> tuple[int, float] | None:
    """Retourne (moves_min, time_s_min) pour le niveau, ou None si jamais termine."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT MIN(moves), MIN(time_s) FROM scores WHERE level = ?",
            (level,),
        ).fetchone()
    if row is None or row[0] is None:
        return None
    return (int(row[0]), float(row[1]))
