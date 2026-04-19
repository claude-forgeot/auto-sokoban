# Contribuer a Auto-Sokoban

Projet 1re annee bachelor, La Plateforme (Marseille). Equipe de 3.
Ce guide est pour les futures contributions (camarades, correcteurs, reprise
personnelle apres soutenance).

## Arborescence

```
auto-sokoban/
  main.py             Point d'entree du jeu
  build-game.py       Compile le jeu en executable (cx_Freeze)
  display-game.py     Prevue les niveaux sans lancer le jeu complet
  game/               Logique metier pure, sans pygame
    board.py          Plateau, etat, regles de deplacement
    level.py          Chargement niveaux XSB, meta (LevelMeta)
    db.py             Scores SQLite dans ~/.auto-sokoban/scores.db
  solver/             Algorithmes de resolution (heritent de Solver ABC)
    base.py           Abstract base class + SolverResult
    bfs.py            Breadth-First Search
    dfs.py            Depth-First Search (limite 200)
    a_star.py         A* avec heuristique Manhattan
  ui/                 Tout ce qui depend de pygame
    audio.py          AudioManager (SFX + musique)
    colors.py         Palette centralisee (BG_PRIMARY, ACCENT_YELLOW, etc.)
    fonts.py          load_font (cache ttf)
    layout.py         BASE_W/BASE_H, scale_font_size, clamp_window_size
    input.py          Action enum, poll_events, Button, _KEY_MAP
    renderer.py       Rendu d'un plateau en pygame.Surface
    metrics_panel.py  Panneau comparatif solveurs (race + solver)
    scenes/           SceneManager + 7 scenes (menu, level_select, game,
                      solver, race, ranking, game_over)
  levels/             52 niveaux XSB (18 faciles, 17 moyens, 17 difficiles)
  assets/             Sprites + audio (WAV/OGG)
  tests/              Tests pytest (120 tests sur solver + board + db)
```

## Ajouter une nouvelle scene

1. Creer `ui/scenes/ma_scene.py` heritant de `Scene` (defini dans `ui/scenes/base.py`).
2. Implementer les methodes : `on_enter()`, `handle_events()`, `update()`,
   `draw(screen)`, `on_resize(new_w, new_h)`.
3. Stocker les parametres : `self.manager`, `self.audio` (optionnel),
   `self.screen_w`, `self.screen_h`.
4. La scene est instanciee par un caller (souvent une autre scene) puis activee
   via `self.manager.switch(new_scene)`.

Squelette minimal :

```python
from ui.audio import AudioManager
from ui.colors import BG_PRIMARY as BG_COLOR
from ui.input import poll_events, Button
from ui.scenes.base import Scene, SceneManager

class MaScene(Scene):
    def __init__(self, manager: SceneManager, audio: AudioManager | None = None,
                 screen_w: int = 800, screen_h: int = 600) -> None:
        super().__init__(manager)
        self.audio = audio
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._buttons: list[Button] = []

    def on_enter(self) -> None:
        self._build_layout()

    def _build_layout(self) -> None:
        # Charger fonts et construire les boutons scales
        ...

    def handle_events(self) -> None:
        actions = poll_events(self._buttons, audio=self.audio)
        ...

    def update(self) -> None:
        ...

    def draw(self, screen) -> None:
        screen.fill(BG_COLOR)
        ...

    def on_resize(self, new_w: int, new_h: int) -> None:
        self.screen_w = new_w
        self.screen_h = new_h
        self._build_layout()
```

## Conventions nommage

- Fichiers : `snake_case.py`.
- Classes : `PascalCase` (ex: `GameScene`, `AudioManager`).
- Fonctions/variables : `snake_case` (ex: `load_level`, `move_count`).
- Constantes module : `SCREAMING_SNAKE_CASE` (ex: `BG_COLOR`, `FPS`).
- Attributs prives : prefixe `_` (ex: `self._buttons`, `self._shake_start`).

## Conventions couleurs

Toutes les couleurs partagees viennent de `ui/colors.py`. Importer sous un
alias semantique local pour preserver la lisibilite :

```python
from ui.colors import BG_PRIMARY as BG_COLOR, ACCENT_YELLOW as TITLE_COLOR
```

Ne jamais recopier un tuple RGB existant. Si besoin d'une nouvelle couleur
partagee, l'ajouter dans `ui/colors.py`.

## Conventions fonts

Utiliser `load_font` + `scale_font_size` pour que les fonts se scalent
proportionnellement a la hauteur de fenetre :

```python
from ui.fonts import load_font
from ui.layout import scale_font_size

self._font_title = load_font(scale_font_size(28, self.screen_h), bold=True)
self._font = load_font(scale_font_size(16, self.screen_h))
```

Les fonts doivent etre reconstruites dans `on_resize` (pas uniquement les
rects de boutons), sinon elles restent a la taille initiale.

## Tests

Lancer les tests :

```bash
python3 -m pytest tests/ -v
```

Convention : un fichier `tests/test_<module>.py` par module teste. Les tests
utilisent pytest + monkeypatch pour isoler les dependances (ex: `_DB_PATH`
redirige vers tmp_path dans `tests/test_db.py`).

Quand une fixture doit intercepter plusieurs attributs module, les patcher
tous (pas seulement celui principal) pour garantir l'isolation.
