"""Gestion du classement en base de donnees SQLite."""

from __future__ import annotations

import sqlite3
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
    conn = _connect()
    conn.execute(
        "INSERT INTO scores (player, level, moves, time_s) VALUES (?, ?, ?, ?)",
        (player, level, moves, round(time_s, 1)),
    )
    conn.commit()
    conn.close()


def get_ranking(level: str, limit: int = 10) -> list[ScoreEntry]:
    """Retourne le classement pour un niveau, trie par coups puis temps."""
    conn = _connect()
    rows = conn.execute(
        "SELECT player, level, moves, time_s, date FROM scores "
        "WHERE level = ? ORDER BY moves ASC, time_s ASC LIMIT ?",
        (level, limit),
    ).fetchall()
    conn.close()
    return [ScoreEntry(*row) for row in rows]


def get_all_ranking(limit: int = 20) -> list[ScoreEntry]:
    """Retourne le classement global tous niveaux confondus."""
    conn = _connect()
    rows = conn.execute(
        "SELECT player, level, moves, time_s, date FROM scores "
        "ORDER BY moves ASC, time_s ASC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [ScoreEntry(*row) for row in rows]
