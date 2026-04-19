"""Gestion audio : musique de fond et effets sonores via pygame.mixer."""

from __future__ import annotations

import logging
from pathlib import Path

import pygame

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "audio"

_SFX_NAMES: tuple[str, ...] = (
    "move", "push", "bottle_clank", "game_start", "race", "win", "button", "game_over",
)
_MUSIC_NAME = "music_loop"
_SUPPORTED_EXT: tuple[str, ...] = (".wav", ".ogg")


class AudioManager:
    """Charge et joue les effets sonores et la musique de fond.

    Tolerant : si un fichier audio est absent, un warning est emis
    et l'appel de lecture correspondant est silencieusement ignore.
    """

    def __init__(self, volume: float = 0.5) -> None:
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_path: Path | None = None
        self._volume = self._clamp_volume(volume)
        self._mixer_ready = False
        
        # MODIFICATION : Ajouter un etat pour tracker le contexte audio actuel
        # Permet de savoir si on est en menu, en jeu, etc. et de gerer
        # correctement la transition entre musique et effets sonores
        self._current_context = "menu"

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

        # Charge chaque effet sonore dans le dictionnaire _sfx
        # La fonction _find_file() cherche le fichier avec les extensions supportees
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

        # Charge la musique de fond
        music_path = self._find_file(_MUSIC_NAME)
        if music_path is not None:
            self._music_path = music_path
        else:
            logger.warning("Musique introuvable : %s (cherche dans %s)", _MUSIC_NAME, _ASSETS_DIR)

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

    # MODIFICATION : Nouvelle methode pour jouer le son de debut de niveau
    def play_game_start(self) -> None:
        """Joue le son de debut de niveau.
        
        Ce son est lance lorsque le joueur entre dans un nouveau niveau
        ou demarre une partie. Il signale le debut du jeu.
        Cette methode arrête aussi la musique de fond et bascule le contexte a "game".
        """
        # Arreter la musique de fond avant de jouer le son de debut
        self.stop_music()
        # Definir le contexte comme etant en jeu
        self._current_context = "game"
        # Jouer le son de debut
        self.play_sfx("game_start")

    # MODIFICATION : Nouvelle methode pour jouer le son de poussee de caisse
    def play_bottle_clank(self) -> None:
        """Joue le son de bouteilles qui s'entrechoquent.
        
        Ce son est lance lors de chaque poussee de caisse pour simuler
        un bruit realiste de bouteilles en verre qui se heurtent.
        """
        self.play_sfx("bottle_clank")
        
        # MODIFICATION : Nouvelle methode pour jouer le son de debut de course
    def play_race_start(self) -> None:
        """Joue le son de début de course algorithmique.
        
        Ce son est lancé lorsque le joueur entre en mode course aux algorithmes.
        Cette méthode arrête aussi la musique de fond et bascule le contexte à "race".
        """
        # Arrêter la musique de fond avant de jouer le son de début de course
        self.stop_music()
        # Définir le contexte comme étant en course
        self._current_context = "race"
        # Jouer le son de début de course
        self.play_sfx("race")

    # ------------------------------------------------------------------
    # Gestion du contexte audio
    # ------------------------------------------------------------------
    
    # MODIFICATION : Nouvelle methode pour retourner au menu
    def return_to_menu(self) -> None:
        """Transition audio du jeu vers le menu.
        
        Arrête tous les sons du jeu et relance la musique de fond du menu.
        Cette methode doit etre appelee quand le joueur quitte une scene de jeu.
        """
        # Arrêter tous les effets sonores qui pourraient jouer
        if self._mixer_ready:
            pygame.mixer.stop()
        # Redéfinir le contexte
        self._current_context = "menu"
        # Relancer la musique de fond
        self.play_music()

    # ------------------------------------------------------------------
    # Musique
    # ------------------------------------------------------------------

    def play_music(self, loops: int = -1) -> None:
        """Lance la musique de fond en boucle (``loops=-1`` = infini)."""
        if not self._mixer_ready or self._music_path is None:
            return
        try:
            pygame.mixer.music.load(str(self._music_path))
            pygame.mixer.music.set_volume(self._volume)
            pygame.mixer.music.play(loops)
        except pygame.error as exc:
            logger.warning("Impossible de lire la musique : %s", exc)

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
        for ext in _SUPPORTED_EXT:
            path = _ASSETS_DIR / f"{name}{ext}"
            if path.is_file():
                return path
        return None