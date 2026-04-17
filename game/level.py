"""Chargement et listing de niveaux Sokoban au format XSB."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from game.board import Board


@dataclass(frozen=True)
class LevelMeta:
    """Metadata d'un niveau."""

    name: str  # identifiant unique : "<difficulte>/<stem>" (ex: "facile/tuto_01")
    path: Path
    difficulty: str  # "facile", "moyen", "difficile"
    box_count: int
    pack: str  # prefixe du fichier (ex: "tuto" pour tuto_01.xsb)
    number: int | None  # suffixe numerique du fichier (ex: 1 pour tuto_01.xsb)


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

_DIFFICULTY_FOLDERS = ("facile", "moyen", "difficile")

_PACK_NUMBER_RE = re.compile(r"^(?P<pack>[A-Za-z]+)_(?P<num>\d+)$")


def _difficulty_from_name(name: str, box_count: int) -> str:
    """Deduit la difficulte du prefixe du fichier, sinon du nombre de caisses.

    Fallback utilise pour la structure a plat (retrocompat avec easy_/medium_/hard_).
    """
    lower = name.lower()
    for prefix, label in _DIFFICULTY_PREFIXES.items():
        if lower.startswith(prefix):
            return label
    if box_count <= 2:
        return "facile"
    if box_count <= 4:
        return "moyen"
    return "difficile"


def _parse_pack_number(stem: str) -> tuple[str, int | None]:
    """Extrait (pack, numero) depuis un nom de fichier <pack>_<num>."""
    m = _PACK_NUMBER_RE.match(stem)
    if m:
        return (m.group("pack"), int(m.group("num")))
    return (stem, None)


def _build_meta(path: Path, difficulty: str, name: str) -> LevelMeta | None:
    """Construit un LevelMeta a partir d'un fichier xsb. Retourne None si invalide."""
    try:
        text = path.read_text(encoding="utf-8")
        Board.from_xsb(text)
    except (ValueError, UnicodeDecodeError) as e:
        print(f"[WARN] Niveau ignore {path.name}: {e}", file=sys.stderr)
        return None
    boxes = _count_boxes(text)
    pack, number = _parse_pack_number(path.stem)
    return LevelMeta(
        name=name,
        path=path,
        difficulty=difficulty,
        box_count=boxes,
        pack=pack,
        number=number,
    )


def list_levels(directory: str | Path) -> list[LevelMeta]:
    """Liste les niveaux .xsb dans un dossier avec leur metadata.

    Structure attendue : <directory>/facile/*.xsb, <directory>/moyen/*.xsb, etc.
    Retrocompat : si aucun sous-dossier de difficulte n'existe, scanne a plat et
    deduit la difficulte depuis le nom ou le nombre de caisses.

    Les fichiers invalides sont ignores avec un warning sur stderr.
    """
    d = Path(directory)
    if not d.is_dir():
        return []

    subdirs = [d / label for label in _DIFFICULTY_FOLDERS if (d / label).is_dir()]

    levels: list[LevelMeta] = []
    if subdirs:
        for sub in subdirs:
            difficulty = sub.name
            for f in sorted(sub.glob("*.xsb")):
                meta = _build_meta(f, difficulty, name=f"{difficulty}/{f.stem}")
                if meta is not None:
                    levels.append(meta)
    else:
        # Retrocompat : structure a plat.
        for f in sorted(d.glob("*.xsb")):
            try:
                text = f.read_text(encoding="utf-8")
                Board.from_xsb(text)
            except (ValueError, UnicodeDecodeError) as e:
                print(f"[WARN] Niveau ignore {f.name}: {e}", file=sys.stderr)
                continue
            boxes = _count_boxes(text)
            pack, number = _parse_pack_number(f.stem)
            levels.append(
                LevelMeta(
                    name=f.stem,
                    path=f,
                    difficulty=_difficulty_from_name(f.stem, boxes),
                    box_count=boxes,
                    pack=pack,
                    number=number,
                )
            )

    levels.sort(key=lambda m: (_DIFFICULTY_FOLDERS.index(m.difficulty) if m.difficulty in _DIFFICULTY_FOLDERS else 99, m.name))
    return levels
