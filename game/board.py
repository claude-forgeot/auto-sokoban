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
        """Retourne 'wall' | 'box' | 'player' | 'target' | 'empty'."""
        if pos in self.walls:
            return "wall"
        if pos in self.boxes:
            return "box"
        if pos == self.player:
            return "player"
        if pos in self.targets:
            return "target"
        return "empty"

    def __hash__(self) -> int:
        """Hash base sur (player, boxes) uniquement."""
        return hash((self.player, self.boxes))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BoardState):
            return NotImplemented
        return self.player == other.player and self.boxes == other.boxes


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

        state = BoardState(
            walls=frozenset(walls),
            targets=frozenset(targets),
            boxes=frozenset(boxes),
            player=player,
            width=width,
            height=height,
        )
        return cls(state)
