"""Scenes du jeu (menu, gameplay, classement)."""

from enum import Enum


class Mode(Enum):
    """Mode de jeu declencheur d'une scene consommatrice (GameScene, SolverScene, RaceScene)."""

    PLAY = "play"
    SOLVE = "solve"
    RACE = "race"
