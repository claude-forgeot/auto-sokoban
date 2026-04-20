"""Chargement et listing de niveaux Sokoban au format XSB."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from game.board import Board

logger = logging.getLogger(__name__)


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
        ValueError: si le contenu XSB est invalide ou chemin malveillant.
    """
    p = Path(path).resolve()
    
    # Vérifier que le chemin est dans le répertoire autorisé
    allowed_dir = Path(__file__).resolve().parent.parent / "levels"
    try:
        p.relative_to(allowed_dir)
    except ValueError:
        raise ValueError(f"Path {path} is outside allowed levels directory")
    
    if not p.exists():
        raise FileNotFoundError(f"Level file not found: {p}")
    
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
        logger.warning("Niveau ignore %s: %s", path.name, e)
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

    Les fichiers invalides sont ignores avec un warning via logger.
    Si au moins un fichier .xsb est present mais qu'aucun n'est valide,
    leve RuntimeError pour eviter un menu de niveaux silencieusement vide.
    """
    d = Path(directory)
    if not d.is_dir():
        return []

    subdirs = [d / label for label in _DIFFICULTY_FOLDERS if (d / label).is_dir()]

    xsb_files: list[Path] = []
    levels: list[LevelMeta] = []
    if subdirs:
        for sub in subdirs:
            difficulty = sub.name
            for f in sorted(sub.glob("*.xsb")):
                xsb_files.append(f)
                meta = _build_meta(f, difficulty, name=f"{difficulty}/{f.stem}")
                if meta is not None:
                    levels.append(meta)
    else:
        # Retrocompat : structure a plat.
        for f in sorted(d.glob("*.xsb")):
            xsb_files.append(f)
            try:
                text = f.read_text(encoding="utf-8")
                Board.from_xsb(text)
            except (ValueError, UnicodeDecodeError) as e:
                logger.warning("Niveau ignore %s: %s", f.name, e)
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

    if xsb_files and not levels:
        raise RuntimeError(
            f"Aucun niveau valide dans {d} ({len(xsb_files)} .xsb trouves, tous invalides)"
        )

    levels.sort(key=lambda m: (_DIFFICULTY_FOLDERS.index(m.difficulty) if m.difficulty in _DIFFICULTY_FOLDERS else 99, m.name))
    return levels
