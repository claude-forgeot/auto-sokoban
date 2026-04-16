# Scenario de demo live

## Duree cible : 3 minutes

## Demo 1 : Jeu humain (Dev 2, ~1:30)

**Niveau** : easy_2 (2 caisses, 10 coups optimal)

1. Lancer le jeu : `python3 main.py`
2. Selectionner "easy_2" dans le menu
3. Cliquer "JOUER"
4. Jouer le niveau en ~30 secondes
5. Montrer le bouton "ANNULER" (defaire un coup)
6. Terminer le niveau
7. Saisir un nom (ex: "Alice")
8. Montrer le classement

## Demo 2 : Resolution automatique (Dev pilote, ~1:30)

**Niveau** : medium_1 (3 caisses, 19 coups optimal)

1. Revenir au menu (bouton "RETOUR MENU")
2. Selectionner "medium_1"
3. Cliquer "JOUER"
4. Cliquer "RESOUDRE" -- transition vers SolverScene
5. Observer le replay A* pas-a-pas
6. Cliquer "ALGO SUIVANT" pour lancer BFS
7. Observer le replay BFS
8. Cliquer "ALGO SUIVANT" pour DFS
9. Montrer le tableau comparatif final

**Points a souligner pendant la demo :**
- A* explore ~5400 noeuds, BFS ~12400, DFS ~1.7M
- A* et BFS trouvent la solution optimale (19 coups)
- DFS trouve 181 coups (non optimal)

## Niveaux de secours

Si un niveau bug en live :
- easy_1 (1 caisse, 3 coups) -- niveau trivial de backup
- medium_2 (4 caisses, 19 coups) -- alternative a medium_1
