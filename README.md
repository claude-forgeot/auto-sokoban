# Auto-Sokoban

Sokoban jouable en Pygame avec trois solveurs automatiques : BFS, DFS et A*.

Projet 1re annee bachelor, La Plateforme (Marseille). Equipe de 3.

## Demarrage

```bash
cd auto-sokoban
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Controles

Fleches directionnelles ou ZQSD pour bouger. U ou Backspace pour annuler,
R pour reset, Echap pour quitter. Le bouton "Resoudre" dans le jeu lance
les trois algos sur le niveau en cours.

## Tests

```bash
python3 -m pytest tests/ -v
```

## Structure

```
game/          Plateau, regles, niveaux, scores SQLite
solver/        BFS, DFS, A* (heritent de Solver ABC dans base.py)
ui/            Scenes Pygame, rendu, boutons, audio
levels/        7 niveaux XSB
assets/        Sprites + sons
tests/         pytest sur les solveurs et le plateau
```

`main.py`, `build-game.py` et `display-game.py` a la racine comme demande
par le sujet.

## Solveurs

BFS explore par niveaux de profondeur. Toujours optimal en nombre de coups
mais ca devient lent quand le nombre de caisses augmente.

DFS part en profondeur d'abord (on a mis une limite a 200 pour eviter les
boucles infinies). Plus rapide parfois mais les solutions sont longues,
voire pas du tout optimales. Ca sert de contre-exemple pour voir pourquoi
BFS est meilleur sur ce type de probleme.

A* c'est comme BFS sauf qu'on guide l'exploration avec la distance
Manhattan entre chaque caisse et la cible la plus proche. Du coup il
explore moins de noeuds pour le meme resultat.

### Benchmarks

Mesures sur nos 7 niveaux (les plus parlants) :

| Niveau | Caisses | Algo | Coups | Noeuds | Temps |
|--------|---------|------|-------|--------|-------|
| easy_1 | 1 | BFS | 3 | 7 | <1ms |
| easy_1 | 1 | DFS | 29 | 89 | <1ms |
| easy_1 | 1 | A* | 3 | 7 | <1ms |
| medium_1 | 3 | BFS | 19 | 12385 | 50ms |
| medium_1 | 3 | DFS | 181 | 1.7M | 7.9s |
| medium_1 | 3 | A* | 19 | 5422 | 32ms |
| hard_1 | 5 | BFS | 25 | 274k | 1.6s |
| hard_1 | 5 | DFS | 200 | 60k | 219ms |
| hard_1 | 5 | A* | 25 | 48k | 412ms |

Le truc frappant c'est medium_1 : DFS met 8 secondes pour trouver 181 coups,
A* met 32ms pour 19 coups. Sur hard_1 BFS explore 274k noeuds, A* seulement
48k pour le meme nombre de coups.

## Fonctionnalites

- Jeu complet (deplacement, poussee, undo, reset)
- 7 niveaux : 3 faciles, 2 moyens, 2 difficiles
- Resolution auto avec replay pas-a-pas
- Comparaison des 3 algos avec metriques
- Classement sauvegarde en SQLite
- Musique + effets sonores
