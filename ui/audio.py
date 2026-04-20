"""Gestion audio : musique de fond et effets sonores via pygame.mixer."""

from __future__ import annotations

import logging
from pathlib import Path

import pygame

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "audio"

_SFX_NAMES: tuple[str, ...] = (
    "move", "push", "bottle_clank", "win", "button", "game_over",
)
_MUSIC_TRACKS: tuple[str, ...] = ("music_loop", "game_start", "race")
_DEFAULT_MUSIC = "music_loop"
_SUPPORTED_EXT: tuple[str, ...] = (".wav", ".ogg")


class AudioManager:
    """Charge et joue les effets sonores et la musique de fond.

    Tolerant : si un fichier audio est absent, un warning est emis
    et l'appel de lecture correspondant est silencieusement ignore.
    """

    def __init__(self, volume: float = 0.5) -> None:
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_paths: dict[str, Path] = {}
        self._volume = self._clamp_volume(volume)
        self._mixer_ready = False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Initialise le mixer et charge les samples depuis assets/."""
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error as exc:
                logger.warning("pygame.mixer.init() a echoue : %s (jeu sans son)", exc)
                return
        self._mixer_ready = True

        for name in _SFX_NAMES:
            path = self._find_file(name)
            if path is None:
                logger.warning("SFX introuvable : %s (cherche dans %s)", name, _ASSETS_DIR)
                continue
            try:
                sound = pygame.mixer.Sound(str(path))
                sound.set_volume(self._volume)
                self._sfx[name] = sound
            except pygame.error as exc:
                logger.warning("Impossible de charger %s : %s", path, exc)

        for name in _MUSIC_TRACKS:
            path = self._find_file(name)
            if path is None:
                logger.warning("Musique introuvable : %s (cherche dans %s)", name, _ASSETS_DIR)
                continue
            self._music_paths[name] = path

    # ------------------------------------------------------------------
    # Effets sonores
    # ------------------------------------------------------------------

    def play_sfx(self, name: str) -> None:
        """Joue l'effet sonore ``name``. Ignore si absent ou mixer inactif."""
        if not self._mixer_ready:
            return
        sound = self._sfx.get(name)
        if sound is not None:
            sound.play()

    def play_bottle_clank(self) -> None:
        self.play_sfx("bottle_clank")

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def return_to_menu(self) -> None:
        """Transition audio vers le menu : stoppe les SFX et relance music_loop."""
        if self._mixer_ready:
            pygame.mixer.stop()
        self.play_music(_DEFAULT_MUSIC)

    # ------------------------------------------------------------------
    # Musique (canal pygame.mixer.music, piste unique remplacable)
    # ------------------------------------------------------------------

    def play_music(self, name: str = _DEFAULT_MUSIC, loops: int = -1) -> None:
        """Charge et joue la piste ``name`` via ``pygame.mixer.music``.

        Chaque appel remplace la piste en cours (load + play), ce qui empeche
        tout chevauchement entre musiques. ``loops=-1`` = boucle infinie,
        ``loops=0`` = lecture unique (jingle).
        """
        if not self._mixer_ready:
            return
        path = self._music_paths.get(name)
        if path is None:
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self._volume)
            pygame.mixer.music.play(loops)
        except pygame.error as exc:
            logger.warning("Impossible de lire la musique %s : %s", name, exc)

    def pause_music(self) -> None:
        """Met la musique en pause."""
        if self._mixer_ready:
            pygame.mixer.music.pause()

    def unpause_music(self) -> None:
        """Reprend la musique apres une pause."""
        if self._mixer_ready:
            pygame.mixer.music.unpause()

    def stop_music(self) -> None:
        """Arrete la musique."""
        if self._mixer_ready:
            pygame.mixer.music.stop()

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    @property
    def volume(self) -> float:
        """Volume courant (0.0 a 1.0)."""
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = self._clamp_volume(value)
        for sound in self._sfx.values():
            sound.set_volume(self._volume)
        if self._mixer_ready:
            pygame.mixer.music.set_volume(self._volume)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp_volume(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _find_file(name: str) -> Path | None:
        """Cherche ``name`` avec les extensions supportees dans assets/."""
        # Valider que name ne contient pas de traversal
        if ".." in name or "/" in name or "\\" in name or name.startswith("/"):
            return None
        
        for ext in _SUPPORTED_EXT:
            path = _ASSETS_DIR / f"{name}{ext}"
            # Vérifier que le chemin reste dans _ASSETS_DIR
            try:
                path.resolve().relative_to(_ASSETS_DIR.resolve())
            except ValueError:
                return None
            
            if path.is_file():
                return path
        return None