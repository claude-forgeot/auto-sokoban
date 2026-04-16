<!-- Slide 1 : A* -->
## A* -- Best-First Search informe

```
f(n) = g(n) + h(n)
g(n) = cout reel depuis le depart
h(n) = heuristique Manhattan (admissible)
```

**Heuristique Manhattan** : somme des distances de chaque  
caisse vers la cible la plus proche.

Admissible = sous-estime toujours le cout reel.  
Donc A* **garantit l'optimalite**, comme BFS,  
mais explore beaucoup moins de noeuds.

---

<!-- Slide 2 : Tableau comparatif -->
## Resultats compares (metriques reelles)

| Niveau     | BFS coups | BFS noeuds | DFS coups | DFS noeuds | A* coups | A* noeuds |
|------------|-----------|------------|-----------|------------|----------|-----------|
| easy_1     | 3         | 7          | 29        | 89         | 3        | 7         |
| easy_3     | 12        | 188        | 16        | 63 029     | 12       | 99        |
| medium_1   | 19        | 12 385     | 181       | 1 708 825  | 19       | 5 422     |
| hard_1     | 25        | 274 131    | 200       | 59 769     | 25       | 48 315    |

- A* trouve la meme solution optimale que BFS
- A* explore 2x a 5x moins de noeuds que BFS
- DFS est rapide mais donne des solutions tres longues

---

<!-- Slide 3 : Conclusion -->
## Conclusion

**A* est le meilleur compromis** pour Sokoban :

- Optimal comme BFS
- Plus rapide grace a l'heuristique
- DFS reste utile pedagogiquement (contre-exemple)

Le projet couvre : jeu jouable, 3 algorithmes compares,  
classement en base de donnees, musique et sons.

Merci ! Questions ?
