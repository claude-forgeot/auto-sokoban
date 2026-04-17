# Post-mortem : merge 51401ac (complete -> main)

**Date de l'incident** : 2026-04-17
**Merge concerne** : `51401ac` (merge `main` into `complete` par Manon)
**Commit de reconciliation** : `5030095`

## Ce qu'il s'est passe

Manon a merge `main` dans sa branche `complete`. Le merge a enregistre une
version simplifiee de `ui/scenes/game.py` qui perdait plusieurs bouts de code
ajoutes cote `main` :

1. Init des flags `_facing_left` (bool) et `_confirm_solve` (bool) dans
   `GameScene.__init__`. Leur absence causait `AttributeError` au runtime
   quand le joueur appuyait sur une fleche.
2. Usage de `load_font(18)` (police pixel custom) remplace par
   `pygame.font.SysFont("monospace", 18)` qui ne rend pas les accents sur
   tous les systemes.
3. Libelles des boutons "REINIT." et "RESOUDRE" perdant leurs accents
   E -> E (probablement a cause d'un copy-paste ASCII).

Ces trois regressions sont passees les tests unitaires (aucun test ne
couvre l'UI Pygame) et n'ont ete detectees qu'en lancant le jeu.

## Impact

- Jeu ne demarre pas (AttributeError en clic sur une fleche au debut du
  premier niveau).
- Texte boutons : accents manquants, rendu incoherent avec le reste du menu.
- Perte de temps : session de reconciliation manuelle pour re-integrer les
  versions des deux cotes.

## Causes racines

1. **Resolution de conflit trop rapide** : lors du merge, la strategie a ete
   "garder la version de sa branche" plutot que "combiner les init des deux".
2. **Pas de verification runtime** : seul `pytest` a ete execute avant le push.
   Les tests ne couvrent pas les scenes Pygame -> AttributeError non detecte.
3. **Deux devs modifient les memes lignes** : changes `GameScene.__init__`
   coexistent sans communication prealable.

## Actions deja prises

- Commit 5030095 : reconcilier `game.py` (init + accents + load_font).
- Commit 5c4b24b (cette session) : remettre `load_font(18)` partout +
  nettoyer les doublons push/bottle_clank laisses par le merge.
- Commit f5d25ef (cette session) : refactor `MenuScene` pour eviter la
  duplication introduite par le merge (grille 52 niveaux vs LevelSelectScene).

## Garde-fous proposes

### Immediat (a appliquer des aujourd'hui)

- Toute PR qui touche `ui/scenes/*.py` doit inclure, dans la description,
  la commande exacte de test runtime utilisee (ex : lancer `main.py` et
  naviguer menu -> jeu -> retour).
- `pytest tests/` seul n'est PAS suffisant pour valider un merge UI.
- Avant de fusionner une PR : `git log --oneline main..pr-branch` pour
  voir ce qui est ajoute, puis `git log --oneline pr-branch..main` pour
  voir ce qu'on risque d'ecraser.

### Moyen terme (a mettre en place si on a le temps)

- Ajouter un smoke test pygame (headless avec `SDL_VIDEODRIVER=dummy`)
  qui fait `on_enter` / `on_resize` sur chaque scene et verifie qu'aucune
  exception n'est levee. Cela aurait attrape l'AttributeError `_facing_left`.
- Hook pre-push qui execute ce smoke test.

### Culture d'equipe

- Avant de toucher `game.py` ou `menu.py` (fichiers chauds), prevenir sur
  le chat equipe pour eviter les conflits multiples.
- Privilegier les PR petites (<300 lignes de diff) pour faciliter la review.
- Utiliser les scopes de commit (`feat(ui):`, `fix(game):`) systematiquement.

## Liens

- Workflow merge/conflit : `docs/workflow-merge.md`
- Commit de reconciliation : `5030095`
- Merge fautif : `51401ac`
