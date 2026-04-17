# Workflow merge / resolution de conflits (Auto-Sokoban)

Ce document decrit le process recommande pour integrer les travaux de chaque
membre de l'equipe (Daisy, Manon, Raymond) sans ecraser du code existant.
Il fait suite au merge 51401ac (Manon -> main) qui a necessite une session
de reconciliation complete.

## Principe

- `main` est la branche de reference : tout le monde part de `main` a jour.
- Chaque feature = une branche courte (`feat/audio-sfx`, `fix/menu-overflow`).
- Un merge vers `main` passe par une PR. Pas de push direct sur `main`.
- Avant de pousser, la branche DOIT etre rebase ou merge a jour avec `main`.

## Pas a pas : integrer ta branche

```bash
# 1. Mettre a jour main localement
git checkout main
git pull origin main

# 2. Revenir sur ta branche et l'integrer
git checkout ma-branche
git merge main        # OU : git rebase main (si la branche n'est pas partagee)

# 3. Resoudre les conflits (voir section ci-dessous)

# 4. Tester (pytest + lancement main.py) avant de pousser
python3 -m pytest tests/
python3 main.py       # verifier qu'aucune scene n'est cassee

# 5. Pousser
git push origin ma-branche
```

Puis creer une PR sur GitHub et demander une review a un coequipier.

## Resoudre un conflit

Quand `git merge main` echoue, Git marque les sections en conflit avec :

```
<<<<<<< HEAD (ta branche)
ton code
=======
code de main
>>>>>>> main
```

### Regles de decision

1. **Ne jamais supprimer en bloc un des deux cotes** sans comprendre son role.
2. Lire le code des DEUX cotes du conflit. Si un cote ajoute une fonctionnalite
   que l'autre ne connait pas, il faut souvent GARDER LES DEUX et les combiner.
3. Si tu ne comprends pas un bout de code, demande a l'auteur avant de decider.
4. Apres resolution, relancer `pytest tests/` ET `main.py` pour valider.

### Exemple concret (tire du merge 51401ac)

Lors du merge `complete -> main` :
- La branche `complete` avait une version simple de `GameScene.on_enter`.
- `main` avait une version enrichie avec `_game_start_sound_played`, `_facing_left`,
  `_confirm_solve` et `load_font`.

Le merge a initialement conserve la version simple, ce qui a CASSE :
- init des variables `_facing_left` et `_confirm_solve` (AttributeError runtime)
- rendu des accents dans les boutons (SysFont au lieu de load_font)

Il a fallu un commit de reconciliation (5030095) pour restaurer les deux.

**Lecon** : quand un fichier a evolue des deux cotes, le merge doit integrer
les deux ensembles d'init, pas choisir l'un ou l'autre.

## Commandes utiles

```bash
# Voir les fichiers en conflit
git diff --name-only --diff-filter=U

# Annuler un merge en cours si on se perd
git merge --abort

# Visualiser les divergences entre deux branches
git log --oneline --graph main..ma-branche
git log --oneline --graph ma-branche..main

# Restaurer un fichier depuis main sans annuler tout le merge
git checkout main -- chemin/du/fichier
```

## Checklist avant de merger

- [ ] `git pull origin main` fait AVANT de merger
- [ ] Tous les conflits resolus manuellement, zero marqueur `<<<<`
- [ ] `pytest tests/` passe (107 tests attendus)
- [ ] `python3 main.py` lance sans crash, navigation menu -> jeu -> retour OK
- [ ] Pas de fichiers non suivis bizarres (`git status`) avant de committer
- [ ] Pas d'emoji dans les commits
- [ ] Scope commit valide : `game`, `solver`, `render`, `ui`, `audio`, `db`,
      `level`, `assets`, `infra`, `docs`

## Qui faire valider ?

- Changements UI visibles -> Daisy (qualite visuelle)
- Changements algo solveur -> Raymond (correction BFS/DFS/A*)
- Changements infra / gitignore / assets -> Manon (W11)
- Merge vers main -> au moins 1 review avant merge
