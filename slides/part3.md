<!-- Slide 1 : Niveaux et BDD -->
## Niveaux et classement

- 7 niveaux au format XSB (standard Sokoban)
- Difficulte detectee depuis le nom du fichier
- Classement SQLite : joueur, niveau, coups, temps, date
- Saisie du nom apres victoire, consultation depuis le menu

```
scores (id, player, level, moves, time_s, date)
ORDER BY moves ASC, time_s ASC
```

---

<!-- Slide 2 : DFS -->
## DFS -- Depth-First Search

```
pile = [(etat_initial, [], 0)]
tant que pile non vide :
    etat, chemin, profondeur = pile.retirer()
    si profondeur >= limite : continuer
    pour chaque direction :
        nouvel_etat = appliquer(etat, direction)
        si gagne : retourner chemin
        si pas visite : pile.ajouter(nouvel_etat)
```

**Explore en profondeur** : rapide mais **ne garantit pas l'optimalite**.  
Utilise comme contre-exemple pedagogique.

---

<!-- Slide 3 : BFS vs DFS -->
## BFS vs DFS -- premier apercu

| Critere       | BFS         | DFS              |
|---------------|-------------|------------------|
| Optimalite    | Oui         | Non              |
| Memoire       | Elevee      | Faible           |
| Completude    | Oui         | Avec limite      |
| Cas d'usage   | Solution courte | Exploration rapide |

DFS trouve une solution mais souvent bien plus longue.  
Il faut un meilleur compromis...
