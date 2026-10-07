# Rush 2 — Pharmaceutical Sales Analysis
*Bootcamp Data Epitech — feuille de route*

---

## 1. Le cadre en une phrase

En tant que consultants, vous transformez 6 ans d'export de caisse d'une pharmacie (8 groupes ATC, janvier 2014 à octobre 2019) en trois choses : une **analyse rigoureuse**, un **outil Excel autonome** et **trois messages distincts** pour trois décideurs. Vous êtes 3 et vous avez 3 jours.

| Interlocuteur | Ce qu'il veut décider |
|---|---|
| **Manager** | L'analyse est-elle solide ? Peut-on vendre une mission de suivi ? |
| **Pharmacien acheteur** | Quoi commander, quels jours, à quelles périodes |
| **Propriétaire** | Que changer dans le fonctionnement, et faut-il accepter l'offre du laboratoire |

---

## 2. Dictionnaire des données

4 exports CSV (`data/raw/`), séparateur `,`, en-tête sur la 1ʳᵉ ligne, aucune valeur vide, aucune valeur négative.

### 2.1 Les fichiers

| Fichier | Lignes | Grain | Première → dernière date | Colonnes |
|---|---|---|---|---|
| `Pharma_Ventes_Hourly.csv` | 50 532 | 1 ligne = 1 heure | `1/2/2014 8:00` → `10/8/2019 19:00` | `datum` + 8 ATC + 4 calendaires |
| `Pharma_Ventes_Daily.csv` | 2 106 | 1 ligne = 1 jour | `1/2/2014` → `10/8/2019` | `datum` + 8 ATC + 4 calendaires |
| `Pharma_Ventes_Weekly.csv` | 302 | 1 ligne = 1 semaine (lun → dim) | `1/5/2014` → `10/13/2019` | `datum` + 8 ATC |
| `Pharma_Ventes_Monthly.csv` | 70 | 1 ligne = 1 mois | `2014-01-31` → `2019-10-31` | `datum` + 8 ATC |

### 2.2 Les colonnes

| Colonne | Fichiers | Type brut (CSV) | Type cible (pandas) | Signification |
|---|---|---|---|---|
| `datum` | tous | texte | `datetime64[ns]` | Date de la période. **Format `m/d/Y`** (+ `H:MM` en horaire) sauf Monthly en **ISO `Y-m-d`**. Weekly : dimanche de **fin** de semaine. Monthly : dernier jour du mois. |
| `M01AB` | tous | décimal | `float64` | Anti-inflammatoires non stéroïdiens, dérivés de l'acide acétique (ex. **diclofénac**) |
| `M01AE` | tous | décimal | `float64` | Anti-inflammatoires non stéroïdiens, dérivés de l'acide propionique (ex. **ibuprofène**) |
| `N02BA` | tous | décimal | `float64` | Analgésiques, acide salicylique et dérivés (ex. **aspirine**) |
| `N02BE` | tous | décimal | `float64` | Analgésiques, anilides (ex. **paracétamol**) — le plus gros volume |
| `N05B` | tous | décimal | `float64` | Psycholeptiques, **anxiolytiques** — donnée sensible |
| `N05C` | tous | entier | `float64` | Psycholeptiques, **hypnotiques et sédatifs** — donnée sensible |
| `R03` | tous | décimal | `float64` | Médicaments des **voies respiratoires obstructives** (asthme, BPCO) |
| `R06` | tous | décimal | `float64` | **Antihistaminiques** à usage systémique (allergies) |
| `Year` | Hourly, Daily | entier | *supprimée* | Année (2014–2019), redondante avec `datum` |
| `Month` | Hourly, Daily | entier | *supprimée* | Mois (1–12), redondant avec `datum` |
| `Hour` | Hourly, Daily | entier | *supprimée* (recalculée en `hour` `Int8` pour l'horaire) | Horaire : heure 0–23. **Journalier : somme des heures de la journée (190–276), sans signification métier** — 276 = 0+1+…+23 |
| `Weekday Name` | Hourly, Daily | texte | *supprimée* | Jour de la semaine en anglais (`Monday`…), redondant avec `datum` |

Les 8 colonnes ATC sont des **quantités enregistrées par le logiciel de caisse** : l'unité n'est pas documentée (boîtes ? unités de prise ?), il ne faut pas l'inventer.

### 2.3 Valeurs observées par groupe ATC

| ATC | Horaire max | Journalier min – max | Mensuel min – max | Quantités non entières (journalier) |
|---|---|---|---|---|
| M01AB | 7 | 0 – 17,3 | 44 – 211 | 1 277 / 2 106 |
| M01AE | 6 | 0 – 14,5 | 37 – 240 | 1 826 / 2 106 |
| N02BA | 6,5 | 0 – 16 | 21 – 194 | 897 / 2 106 |
| N02BE | 29 | 1,2 – 161 | 295 – 1 830 | 1 262 / 2 106 |
| N05B | 15 | 0 – 54,8 | 86 – 525 | 37 / 2 106 |
| N05C | 6 | 0 – 9 | 5 – 50 | 0 |
| R03 | 25 | 0 – 45 | 37 – 432 | 5 / 2 106 |
| R06 | 5 | 0 – 15 | 11 – 213 | 244 / 2 106 |

Les quantités décimales sont fréquentes (fractions de boîte probables) : à **signaler**, pas à arrondir.

### 2.4 Points d'attention

- **Couverture horaire** : 24 lignes par jour (0 h – 23 h, y compris la nuit), sauf le 1ᵉʳ jour (début 8 h) et le dernier (fin 19 h) : 2 106 × 24 − 12 = 50 532.
- **Aucun jour manquant** dans le journalier entre le 02/01/2014 et le 08/10/2019.
- **Périodes partielles** : la 1ʳᵉ semaine (jeu → dim), janvier 2014 (à partir du 2), la dernière semaine (s'arrête le mardi 8/10) et **octobre 2019 (8 jours seulement)**, bien que daté du 31 dans Monthly.
- **Valeurs flottantes bruitées** dans Monthly (`99.75000000000003`) : résidus d'addition, arrondir à la comparaison.
- **Données sensibles** : N05B et N05C au grain horaire présentent un risque de réidentification (voir Objectif G).

---

## 3. Les objectifs et comment les atteindre

### Objectif A : fiabiliser les données (à faire en premier)

Le sujet le dit clairement : les 4 fichiers (horaire, journalier, hebdomadaire, mensuel) n'ont **jamais été réconciliés**. C'est un test implicite.

- **Réagréger** l'horaire en journalier, puis le journalier en hebdomadaire et en mensuel, et **comparer** avec les fichiers fournis. Noter chaque écart.
- Rechercher les **jours manquants**, les doublons, les valeurs négatives ou aberrantes, et les quantités non entières.
- Vérifier si le **dernier mois (octobre 2019) est incomplet**. Si c'est le cas, il ne doit servir ni aux statistiques mensuelles ni à l'évaluation des prévisions.
- **Unité non documentée** : ne pas l'inventer. Parler de « quantités enregistrées par le logiciel » et signaler cette limite.
- Choisir une **source de référence par usage** (par exemple l'horaire pour les profils de la journée, le journalier pour le reste) et la justifier.

> **Résultat :** la feuille *État des données* du classeur (sources, corrections, exclusions, raisons).

### Objectif B : statistiques descriptives utiles à une décision

Ne pas calculer tout ce qui est possible : choisir ce qui soutient une conclusion.

- Volumes et parts par groupe ATC, avec la tendance pluriannuelle.
- **Saisonnalité** mensuelle (le R06, antihistaminiques, au printemps ; le R03 et le N02BE en hiver, par exemple).
- Profils par **jour de la semaine** et par **heure**, utiles pour le personnel et le réassort.
- Variabilité (coefficient de variation), utile pour dimensionner le stock de sécurité.

### Objectif C : un pipeline Python reproductible

- Un seul point d'entrée (par exemple `python main.py`) qui lit les 4 exports, contrôle leur cohérence, calcule les statistiques et **régénère le classeur**.
- Il doit fonctionner **depuis un clone vierge** : chemins relatifs, `requirements.txt`, aucun chemin local.
- Il doit absorber un **mois supplémentaire sans modification** : aucune date ni dimension codée en dur.
- Les statistiques du classeur doivent **venir du code**, pas d'un copier-coller.

### Objectif D : l'outil client dans Excel, sans macro

Le besoin : sélectionner un ou plusieurs groupes ATC et un jour ou une période, puis voir les ventes immédiatement.

- **Approche robuste** : Python écrit une table de données propre (format long : date, heure, ATC, quantité). La feuille outil utilise des **listes déroulantes (validation des données)** et des formules Excel 365 (`FILTER`, `SUMIFS`, `LET`), ou bien un tableau croisé dynamique avec **segments et chronologie**.
- Attention : générer des tableaux croisés ou des segments avec openpyxl est fragile. La solution la plus sûre est un **modèle `.xlsx`** contenant l'outil, dans lequel Python ne réécrit que les feuilles de données.
- Le tester comme un utilisateur qui n'a jamais ouvert Python : aucune formule cassée, aucune manipulation cachée.

### Objectif E : intégrer une donnée publique externe

La donnée doit être **dans l'analyse**, pas seulement citée sur une slide, et servir au moins une recommandation. Quelques pistes cohérentes :

- **Réseau Sentinelles / Santé publique France** (incidence hebdomadaire des syndromes grippaux), à croiser avec N02BE (paracétamol) et R03.
- **Pollens (RNSA)** ou **météo (Météo-France, data.gouv.fr)**, à croiser avec R06.
- **Jours fériés et vacances scolaires** (data.gouv.fr), pour expliquer des creux ou des pics.

Cela répond à la question du propriétaire : quelle part vient de la pharmacie, quelle part de son environnement. Mesurer une corrélation, ou mieux, l'apport de cette variable à un modèle. Ne pas se contenter d'une superposition de courbes.

### Objectif F : la question de prévision (probablement le point le plus noté)

> *« Peut-on prévoir, pour chaque groupe, les ventes du mois qui suit le dernier mois complet ? »*

Protocole minimal défendable :

1. **Définir précisément la cible** : le dernier mois complet (probablement septembre 2019, à confirmer à l'étape A) et donc le mois à prévoir.
2. **Baselines naïves** obligatoires, car c'est la « prévision la plus simple que n'importe qui ferait » :
   - naïf : mois M = mois M-1,
   - naïf saisonnier : mois M = même mois de l'année précédente.
3. **Un ou deux modèles** (lissage exponentiel ETS, SARIMA, voire régression avec variable exogène).
4. **Backtest à origine glissante** : on prévoit le mois M uniquement avec les données jusqu'à M-1, sur 12 à 24 mois de test. **Aucune validation croisée aléatoire**, qui ferait fuiter le futur dans l'entraînement.
5. **Métriques** : MAE ou MAPE par groupe, et surtout la **MASE** ou le gain relatif par rapport à la baseline.
6. **Réponse par groupe** : « oui », « non » ou « seulement pour certains ». Un modèle qui ne bat pas la baseline naïve signifie « non » pour ce groupe. C'est une réponse acceptable, et honnête.

### Objectif G : analyse des risques du partage de données

- **Réidentification** : dans une petite officine, la donnée **horaire** sur N05B (anxiolytiques) et N05C (hypnotiques) peut révéler qu'une personne connue, aperçue au comptoir à 14 h, a acheté un anxiolytique. On parle alors potentiellement de **donnée de santé (art. 9 RGPD)**. Le risque diminue avec l'agrégation : horaire > journalier > hebdomadaire > mensuel.
- **Au-delà du RGPD** (articles à vérifier avant de les citer) :
  - **secret professionnel du pharmacien** (Code de la santé publique, R.4235-5),
  - **dispositif anti-cadeaux** (CSP, L.1453-3 et suivants) : des conditions d'achat accordées en contrepartie de données peuvent être qualifiées d'avantage interdit,
  - **indépendance professionnelle** (code de déontologie), dépendance commerciale envers un laboratoire, confidentialité des données commerciales de l'officine.
- **Recommandation attendue** : une position tranchée et argumentée, par exemple « refus », ou « seulement en mensuel, seuils de suppression appliqués, sans N05B/N05C, sous contrat et après avis juridique ou ordinal ».

### Objectif H : trois messages réellement différents

> ⚠️ Trois decks qui ne diffèrent que par la slide de titre seront comptés comme un seul.

| Deck | Message central | Contenu clé |
|---|---|---|
| **Manager** | « L'analyse tient, et voici la mission de suivi à vendre » | Méthode, qualité des données, résultat du backtest, offre de suivi (rafraîchissement mensuel automatisé) |
| **Pharmacien acheteur** | « Voici quand et quoi commander » | Saisonnalité par groupe, jours et heures de pointe, démonstration de l'outil, groupes prévisibles ou non |
| **Propriétaire** | « Voici ce qu'il faut changer, et notre recommandation sur l'offre du laboratoire » | Effets internes et externes (donnée publique), recommandations opérationnelles, risques du partage |

5 slides maximum et 5 minutes chacun : **une décision par deck**.

---

## 4. Les livrables (tous dans le dépôt Git)

| # | Livrable | Contenu obligatoire |
|---|---|---|
| 1 | **Classeur `.xlsx`** | Feuille de synthèse, statistiques descriptives, état des données, outil de sélection |
| 2 | **Code Python** | Régénère les statistiques depuis les exports, fonctionne depuis un clone vierge |
| 3 | **3 decks** (5 slides max) | Manager, pharmacien acheteur, propriétaire |
| 4 | **Mémo PDF** | Partie 1 : réponse sur la prévision. Partie 2 : analyse des risques du partage |
| 5 | **3 oraux de 5 minutes** | Un par deck, devant un membre de l'équipe pédagogique qui joue le rôle |
| 6 | **Le dépôt lui-même** | Historique montrant le travail partagé, README indiquant **qui a fait quoi**, exports inclus, **rien d'inutile** (pas de venv, de brouillons ni de `__pycache__`, avec un `.gitignore` propre) |

> ⚠️ L'historique Git est évalué : tout le monde committe régulièrement, pas un push massif la dernière nuit.

---

## 5. Proposition de répartition et de planning

| | Personne 1 : Data/Pipeline | Personne 2 : Modélisation | Personne 3 : Outil et communication |
|---|---|---|---|
| **J1** | Réconciliation des 4 exports, état des données | Récupération de la donnée publique, cadrage de la cible | Structure du classeur, maquette de l'outil |
| **J2** | Statistiques descriptives, génération du `.xlsx` | Baselines, modèles, backtest | Outil finalisé, recherches RGPD et CSP |
| **J3 matin** | Test depuis un clone vierge, README | Rédaction de la partie 1 du mémo | Partie 2 du mémo, 3 decks |
| **J3 après-midi** | Répétitions croisées des 3 oraux (chacun présente au moins un deck) | | |

---

## 6. Checklist finale avant rendu

- [ ] Le code tourne depuis un `git clone` vierge avec `pip install -r requirements.txt` puis une seule commande
- [ ] Toutes les statistiques du classeur sont produites par le code
- [ ] La feuille *État des données* liste sources, écarts, corrections et exclusions
- [ ] L'outil fonctionne sans macro dans Excel 365 (multi-sélection ATC et période)
- [ ] La donnée publique est intégrée dans l'analyse et sert au moins une recommandation
- [ ] Le backtest compare chaque modèle aux baselines naïves, avec une réponse par groupe
- [ ] Le mémo PDF contient les 2 parties
- [ ] Les 3 decks portent 3 messages et 3 décisions différents
- [ ] Le README indique qui a fait quoi ; l'historique Git montre les contributions des 3 membres
- [ ] Aucun fichier inutile dans le dépôt