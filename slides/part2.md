<!-- Slide 1 : Jeu jouable -->
## Le jeu Sokoban

- Deplacer les caisses sur les cibles avec les fleches
- Boutons : annuler, reinitialiser, resoudre, quitter
- 7 niveaux (facile, moyen, difficile)
- Musique et effets sonores
- Classement sauvegarde en base de donnees

<!-- Screenshot ou GIF du jeu a inserer ici -->

---

<!-- Slide 2 : BFS -->
## BFS -- Breadth-First Search

```
file = [(etat_initial, [])]
tant que file non vide :
    etat, chemin = file.retirer()
    pour chaque direction :
        nouvel_etat = appliquer(etat, direction)
        si gagne : retourner chemin
        si pas visite : file.ajouter(nouvel_etat)
```

**Explore couche par couche** : garantit la solution optimale  
en nombre de mouvements.

---

<!-- Slide 3 : Visualisation -->
## Resolution visualisee

- Replay pas-a-pas de la solution trouvee
- Tableau de metriques : noeuds explores, temps, coups
- Enchainement automatique des 3 algorithmes
- Comparaison visuelle des performances

<!-- Capture de la SolverScene a inserer ici -->
