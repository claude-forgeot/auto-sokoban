"""Chargement et listing de niveaux Sokoban au format XSB."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from game.board import Board


@dataclass(frozen=True)
class LevelMeta:
    """Metadata d'un niveau."""

    name: str
    path: Path
    difficulty: str  # "facile", "moyen", "difficile"
    box_count: int


def load_level(path: str | Path) -> Board:
    """Charge un fichier XSB et retourne un Board.

    Raises:
        FileNotFoundError: si le fichier n'existe pas.
        ValueError: si le contenu XSB est invalide.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return Board.from_xsb(text)


def _count_boxes(text: str) -> int:
    """Compte les caisses dans un texte XSB."""
    return text.count("$") + text.count("*")


_DIFFICULTY_PREFIXES = {
    "easy": "facile",
    "medium": "moyen",
    "hard": "difficile",
}


def _difficulty_from_name(name: str, box_count: int) -> str:
    """Deduit la difficulte du prefixe du fichier, sinon du nombre de caisses."""
    lower = name.lower()
    for prefix, label in _DIFFICULTY_PREFIXES.items():
        if lower.startswith(prefix):
            return label
    if box_count <= 2:
        return "facile"
    if box_count <= 4:
        return "moyen"
    return "difficile"


def list_levels(directory: str | Path) -> list[LevelMeta]:
    """Liste les niveaux .xsb dans un dossier avec leur metadata.

    Retourne une liste triee par nom de fichier.
    Les fichiers invalides sont ignores avec un warning sur stderr.
    """
    import sys

    d = Path(directory)
    if not d.is_dir():
        return []

    levels: list[LevelMeta] = []
    for f in sorted(d.glob("*.xsb")):
        try:
            text = f.read_text(encoding="utf-8")
            boxes = _count_boxes(text)
            Board.from_xsb(text)  # valide le contenu
            levels.append(
                LevelMeta(
                    name=f.stem,
                    path=f,
                    difficulty=_difficulty_from_name(f.stem, boxes),
                    box_count=boxes,
                )
            )
        except (ValueError, UnicodeDecodeError) as e:
            print(f"[WARN] Niveau ignore {f.name}: {e}", file=sys.stderr)

    return levels
