"""Plateau Sokoban : Direction, BoardState (immuable), Board (mutable)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

Position = tuple[int, int]  # (row, col)


class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

    @property
    def delta(self) -> tuple[int, int]:
        """Offset (drow, dcol) a appliquer a une position."""
        return self.value


@dataclass(frozen=True)
class BoardState:
    """Etat immuable et hashable d'un plateau Sokoban."""

    walls: frozenset[Position]
    targets: frozenset[Position]
    boxes: frozenset[Position]
    player: Position
    width: int
    height: int

    def is_won(self) -> bool:
        """True si toutes les caisses sont sur des cibles."""
        return self.boxes == self.targets

    def at(self, pos: Position) -> str:
        """Retourne l'etat de la case.

        Valeurs : 'wall' | 'box' | 'box_on_target' | 'player' |
        'player_on_target' | 'target' | 'empty'. Les variantes '_on_target'
        permettent au rendu de differencier une caisse/joueur pose sur cible.
        """
        if pos in self.walls:
            return "wall"
        on_target = pos in self.targets
        if pos in self.boxes:
            return "box_on_target" if on_target else "box"
        if pos == self.player:
            return "player_on_target" if on_target else "player"
        if on_target:
            return "target"
        return "empty"

    def __hash__(self) -> int:
        """Hash base sur tous les champs d'identite du plateau.

        Inclut walls et targets pour que deux BoardStates de niveaux
        differents ne soient pas consideres egaux s'ils partagent
        joueur et caisses. Le cache de hash interne des frozenset
        rend cette inclusion quasi-gratuite apres premier calcul.
        """
        return hash((self.player, self.boxes, self.walls, self.targets))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BoardState):
            return NotImplemented
        return (
            self.player == other.player
            and self.boxes == other.boxes
            and self.walls == other.walls
            and self.targets == other.targets
        )


class Board:
    """Wrapper mutable autour de BoardState pour le gameplay."""

    def __init__(self, initial: BoardState) -> None:
        self._initial: BoardState = initial
        self._state: BoardState = initial
        self._history: list[BoardState] = []

    @property
    def state(self) -> BoardState:
        """Etat courant (lecture seule)."""
        return self._state

    def move(self, direction: Direction) -> bool:
        """Tente de deplacer le joueur. Retourne True si le mouvement a eu lieu."""
        dr, dc = direction.delta
        pr, pc = self._state.player
        new_r, new_c = pr + dr, pc + dc
        new_pos = (new_r, new_c)

        if new_pos in self._state.walls:
            return False

        if new_pos in self._state.boxes:
            beyond = (new_r + dr, new_c + dc)
            if beyond in self._state.walls or beyond in self._state.boxes:
                return False
            new_boxes = (self._state.boxes - {new_pos}) | {beyond}
            self._history.append(self._state)
            self._state = BoardState(
                walls=self._state.walls,
                targets=self._state.targets,
                boxes=new_boxes,
                player=new_pos,
                width=self._state.width,
                height=self._state.height,
            )
            return True

        self._history.append(self._state)
        self._state = BoardState(
            walls=self._state.walls,
            targets=self._state.targets,
            boxes=self._state.boxes,
            player=new_pos,
            width=self._state.width,
            height=self._state.height,
        )
        return True

    def undo(self) -> bool:
        """Annule le dernier mouvement. Retourne False si historique vide."""
        if not self._history:
            return False
        self._state = self._history.pop()
        return True

    def reset(self) -> None:
        """Restaure l'etat initial et vide l'historique."""
        self._state = self._initial
        self._history.clear()

    def is_won(self) -> bool:
        return self._state.is_won()

    def was_last_push(self) -> bool:
        """True si le dernier mouvement a pousse une caisse."""
        if not self._history:
            return False
        return self._history[-1].boxes != self._state.boxes

    @classmethod
    def from_xsb(cls, xsb: str) -> Board:
        """Construit un Board depuis le format XSB standard.

        Caracteres : '#' wall, ' ' empty, '.' target, '$' box,
        '*' box on target, '@' player, '+' player on target.
        """
        walls: set[Position] = set()
        targets: set[Position] = set()
        boxes: set[Position] = set()
        player: Position | None = None

        lines = xsb.strip().splitlines()
        height = len(lines)
        width = max(len(line) for line in lines) if lines else 0

        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                pos = (r, c)
                if ch == "#":
                    walls.add(pos)
                elif ch == ".":
                    targets.add(pos)
                elif ch == "$":
                    boxes.add(pos)
                elif ch == "*":
                    boxes.add(pos)
                    targets.add(pos)
                elif ch == "@":
                    player = pos
                elif ch == "+":
                    player = pos
                    targets.add(pos)

        if player is None:
            raise ValueError("Niveau XSB invalide : pas de joueur (@/+).")
        if len(boxes) != len(targets):
            raise ValueError(
                f"Niveau XSB invalide : {len(boxes)} caisses pour {len(targets)} cibles."
            )
        if player in walls:
            raise ValueError(f"Niveau XSB invalide : joueur sur un mur en {player}.")
        overlap_boxes = boxes & walls
        if overlap_boxes:
            raise ValueError(
                f"Niveau XSB invalide : {len(overlap_boxes)} caisse(s) sur un mur : {sorted(overlap_boxes)}"
            )
        overlap_targets = targets & walls
        if overlap_targets:
            raise ValueError(
                f"Niveau XSB invalide : {len(overlap_targets)} cible(s) sur un mur : {sorted(overlap_targets)}"
            )
        if player in boxes:
            raise ValueError(f"Niveau XSB invalide : joueur sur une caisse en {player}.")

        state = BoardState(
            walls=frozenset(walls),
            targets=frozenset(targets),
            boxes=frozenset(boxes),
            player=player,
            width=width,
            height=height,
        )
        return cls(state)


def detect_corner_deadlocks(state: BoardState) -> set[Position]:
    """Retourne les caisses bloquees dans un coin (2 murs orthogonaux adjacents).

    Une caisse sur une cible n'est jamais consideree en deadlock meme si elle
    est dans un coin : le niveau reste gagne.
    """
    deadlocks: set[Position] = set()
    for row, col in state.boxes:
        if (row, col) in state.targets:
            continue
        up = (row - 1, col) in state.walls
        down = (row + 1, col) in state.walls
        left = (row, col - 1) in state.walls
        right = (row, col + 1) in state.walls
        if (up and left) or (up and right) or (down and left) or (down and right):
            deadlocks.add((row, col))
    return deadlocks


def _is_frozen(box: Position, state: BoardState, visited: set[Position]) -> bool:
    """True si la caisse ne peut bouger ni sur l'axe horizontal ni vertical.

    Algorithme axis-by-axis (Sokoban Wiki). `visited` protege contre les
    cycles en traitant les caisses deja en cours d'evaluation comme
    pessimistiquement frozen.
    """
    if box in visited:
        return True
    visited.add(box)
    try:
        return _is_frozen_axis(box, state, visited, horizontal=True) and \
               _is_frozen_axis(box, state, visited, horizontal=False)
    finally:
        visited.discard(box)


def _is_frozen_axis(
    box: Position, state: BoardState, visited: set[Position], horizontal: bool
) -> bool:
    """True si la caisse ne peut bouger sur l'axe donne (un cote suffit)."""
    r, c = box
    if horizontal:
        n1, n2 = (r, c - 1), (r, c + 1)
    else:
        n1, n2 = (r - 1, c), (r + 1, c)
    return _is_blocker(n1, state, visited) or _is_blocker(n2, state, visited)


def _is_blocker(pos: Position, state: BoardState, visited: set[Position]) -> bool:
    """Une case est bloquante si c'est un mur ou une caisse (recursivement) frozen."""
    if pos in state.walls:
        return True
    if pos in state.boxes:
        return _is_frozen(pos, state, visited)
    return False


def detect_freeze_deadlocks(state: BoardState) -> set[Position]:
    """Retourne les caisses frozen : incapables de bouger sur les deux axes.

    Extension recursive de detect_corner_deadlocks : une caisse entouree d'une
    autre caisse frozen est elle-meme frozen. Les caisses frozen sur cible ne
    posent pas probleme en soi mais sont retournees pour affichage.
    Utiliser is_lost() pour savoir si l'etat est perdu.
    """
    frozen: set[Position] = set()
    for box in state.boxes:
        if _is_frozen(box, state, set()):
            frozen.add(box)
    return frozen


def is_lost(state: BoardState) -> bool:
    """True si au moins une caisse frozen est hors cible (niveau perdu)."""
    if state.is_won():
        return False
    return any(
        box not in state.targets for box in detect_freeze_deadlocks(state)
    )
