# Mission — Analyse des ventes d'une officine

*Note de cadrage de l'équipe : ce qu'on nous demande, ce qu'on va répondre, et comment on va y arriver.*
*Pour le code : `ARCHITECTURE.MD`. Pour qui fait quoi et quand : `TACHES.md`. Pour le sujet et les données : `context.MD`.*

---

## 1. La mission

Nous intervenons comme **consultants** pour une pharmacie d'officine. Elle nous confie 6 ans d'exports de son logiciel de caisse (janvier 2014 → octobre 2019, 8 groupes de médicaments ATC, aux grains horaire, journalier, hebdomadaire et mensuel) et attend de nous trois choses :

1. une **analyse rigoureuse** de ses ventes ;
2. un **outil Excel autonome** pour explorer ses ventes sans nous ;
3. une **réponse claire à chacun de ses trois décideurs**.

### Le client et ses questions

| Décideur | Sa question | Ce qu'il doit pouvoir décider après notre passage |
|---|---|---|
| **Manager** (cabinet) | L'analyse est-elle solide ? | Vendre ou non une **mission de suivi** au client |
| **Pharmacien acheteur** | Quoi commander, quels jours, à quelles périodes ? | Adapter ses **commandes et son stock** par groupe |
| **Propriétaire** | Que changer dans le fonctionnement ? Faut-il accepter l'offre du laboratoire qui veut ses données ? | Ses **priorités opérationnelles** et un **oui / non / sous conditions** sur le partage |

### La question centrale

> **Peut-on prévoir, pour chaque groupe ATC, les ventes du mois qui suit le dernier mois complet ?**

La réponse attendue est **par groupe** : « oui », « non » ou « seulement pour certains ». Un « non » démontré est une réponse valable.

---

## 2. Ce que nous livrons

| # | Livrable | Contenu | Pour qui |
|---|---|---|---|
| 1 | **Classeur `Analyse_Pharma.xlsx`** | Synthèse, statistiques, état des données, prévisions, outil de sélection ATC × période | Pharmacien, propriétaire |
| 2 | **Pipeline Python** | `python main.py` régénère tout depuis les exports, depuis un clone vierge, sans modification si un mois est ajouté | Manager (preuve de sérieux, base de la mission de suivi) |
| 3 | **3 decks** de 5 slides max | Un message et une décision par décideur | Les trois |
| 4 | **Mémo PDF** | Partie 1 : la prévision. Partie 2 : les risques du partage de données | Manager, propriétaire |
| 5 | **3 oraux de 5 min** | Un par deck | Jury dans le rôle du décideur |
| 6 | **Le dépôt Git** | Historique partagé, README « qui a fait quoi », rien d'inutile | Jury |

---

## 3. Comment nous allons y répondre

### 3.1 D'abord, fiabiliser les données

**Pourquoi en premier :** les 4 exports n'ont jamais été réconciliés. Toute conclusion bâtie sur un export faux est fausse.

**Comment :**
- Charger les 4 exports dans un format unique (date, heure, ATC, quantité, source).
- Réagréger l'horaire en journalier, puis le journalier en hebdomadaire et en mensuel, et **comparer** aux fichiers fournis.
- Contrôler trous, doublons, valeurs négatives, quantités non entières, mois incomplets.
- **Choisir une source de référence par usage** et tracer chaque décision dans la feuille « État des données ».

**Ce que nous avons déjà établi :**

| Constat | Décision |
|---|---|
| Horaire, journalier et hebdomadaire concordent exactement | Journalier = référence ; horaire pour les profils intra-journée ; hebdo = contrôle seulement |
| **Le mensuel fourni est faux** sur 45 cellules sur 560 (jusqu'à +75 % en octobre 2014) | Mensuel **écarté**, recalculé depuis le journalier |
| Octobre 2019 ne couvre que 8 jours | Exclu des stats mensuelles et de la prévision, conservé pour les profils jour/heure |
| Aucun trou, doublon ni négatif | Rien à corriger |
| Nombreuses quantités décimales, unité non documentée | Conservées, signalées ; on parle de « quantités enregistrées par le logiciel » |

### 3.2 Décrire ce qui sert une décision

On ne calcule pas tout ce qui est possible, seulement ce qui soutient une recommandation :

| Analyse | Décision qu'elle éclaire |
|---|---|
| Volumes, parts et tendance par ATC | Sur quels groupes concentrer l'attention |
| Saisonnalité mensuelle (hypothèses : R06 au printemps, R03 et N02BE en hiver) | **Quand** renforcer les commandes |
| Profils jour de la semaine et heure | **Quels jours** réassortir, quand renforcer le comptoir |
| Coefficient de variation, stock de sécurité | **Combien** garder en stock par groupe |

### 3.3 Répondre à la question de prévision

Protocole défendable devant un manager :

1. **Cible** : le mois suivant le dernier mois complet, calculé depuis les données (septembre 2019 complet → **octobre 2019** à prévoir).
2. **Baselines obligatoires** : naïf (M = M-1) et naïf saisonnier (M = même mois de l'année précédente) — « ce que n'importe qui ferait ».
3. **Modèle** : lissage exponentiel (ETS) ; SARIMA et régression exogène si le temps le permet.
4. **Backtest à origine glissante** sur 24 mois : chaque mois est prévu uniquement avec les données antérieures. Un test automatique garantit qu'aucune donnée future ne fuite.
5. **Métriques** : MAE, MAPE et surtout **MASE** et gain par rapport aux baselines.
6. **Verdict par groupe** : « oui » si le modèle bat les deux baselines, sinon « non ».

### 3.4 Intégrer une donnée publique

Objectif : séparer ce qui vient de la pharmacie de ce qui vient de son environnement.

- **Source retenue** : incidence hebdomadaire des syndromes grippaux (Réseau Sentinelles), croisée avec N02BE (paracétamol) et R03. Repli : jours fériés et vacances scolaires (data.gouv.fr).
- **Méthode** : corrélation sur les écarts à la saisonnalité (pas sur les courbes brutes), et si possible apport de la variable au modèle de prévision.
- **Usage** : au moins une recommandation au propriétaire repose dessus.

### 3.5 Évaluer l'offre du laboratoire

Analyse des risques du partage des données de vente :

- **Réidentification** : au grain horaire, dans une petite officine, les ventes d'anxiolytiques (N05B) et d'hypnotiques (N05C) peuvent désigner une personne → donnée de santé (RGPD art. 9). Le risque baisse avec l'agrégation.
- **Au-delà du RGPD** (articles à vérifier avant citation) : secret professionnel (CSP R.4235-5), dispositif anti-cadeaux (CSP L.1453-3 et suivants), indépendance professionnelle, dépendance commerciale.
- **Position attendue** : tranchée et argumentée, par exemple « refus », ou « mensuel uniquement, sans N05B/N05C, seuils de suppression, sous contrat et après avis juridique ».

### 3.6 Livrer un outil utilisable sans nous

- Python écrit des **tables de données propres** dans un **modèle Excel** préparé à la main.
- La feuille Outil utilise des **listes déroulantes et des formules Excel 365** (`FILTER`, `SUMIFS`), sans macro.
- Test final : quelqu'un qui n'a jamais ouvert Python sélectionne un groupe et une période et voit ses ventes.

---

## 4. Les trois messages

Trois decks qui ne diffèrent que par le titre comptent pour un seul : chaque deck porte **une décision**.

| Deck | Message central | Preuves |
|---|---|---|
| **Manager** | « L'analyse tient, et voici la mission de suivi à vendre. » | Méthode, réconciliation (mensuel faux détecté), backtest vs baselines, pipeline qui se rafraîchit chaque mois |
| **Pharmacien acheteur** | « Voici quand et quoi commander. » | Saisonnalité par groupe, jours et heures de pointe, démo de l'outil, groupes prévisibles ou non |
| **Propriétaire** | « Voici ce qu'il faut changer, et notre position sur l'offre du laboratoire. » | Effets internes vs externes (donnée publique), recommandations opérationnelles, risques du partage |

*Les chiffres des decks viendront du pipeline ; aucun résultat n'est écrit ici avant d'être calculé.*

---

## 5. Comment nous travaillons

### Organisation

Deux rôles qui ne se touchent que via des formats de données figés (`ARCHITECTURE.MD` §3 et §7.2) :

| | **A — Données → Classeur** | **B — Prévision & environnement** |
|---|---|---|
| Question portée | « Les données sont-elles fiables, et le client peut-il s'en servir ? » | « Peut-on prévoir, et qu'est-ce qui vient de l'extérieur ? » |
| Code | chargement, qualité, nettoyage, stats descriptives, Excel | donnée externe, prévision, saisonnalité, variabilité, figures |
| Mémo | Partie 2 : risques du partage | Partie 1 : prévision |
| Deck | Propriétaire | Manager |
| Ensemble | Deck Pharmacien, répétition des 3 oraux | |

Détail des tâches et planning : `TACHES.md`.

### Principes

- **Une seule commande** : `python main.py` reproduit tout, depuis un clone vierge.
- **Rien en dur** : ni date, ni groupe ATC, ni chemin local. Un mois de plus ne demande aucune modification.
- **Tout chiffre vient du code** : pas de copier-coller dans le classeur ni dans les decks.
- **Chaque décision sur les données est tracée** avec sa raison dans « État des données ».
- **Honnêteté** : un groupe imprévisible est annoncé comme tel ; l'unité non documentée n'est pas inventée.
- **Git** : une branche par module, PR relue par l'autre, petits commits réguliers des deux membres.

### Calendrier

| Jour | Objectif |
|---|---|
| **J1** ✅ | Socle du code, chargement et contrôle des données, constats qualité |
| **J2** | Prévision et backtest, donnée externe, stats, classeur Excel — **code gelé le soir** |
| **J3 matin** | Mémo, decks, test depuis un clone vierge, README |
| **J3 après-midi** | Répétition croisée des 3 oraux |

---

## 6. Risques du projet et parades

| Risque | Parade |
|---|---|
| La prévision (point le plus noté) n'est pas prête | Baselines + backtest + ETS d'abord ; SARIMA et exogène en bonus seulement |
| Le téléchargement de la donnée externe échoue | Repli sur jours fériés / vacances ; cache commité dans `data/external/` |
| Le classeur généré est cassé dans Excel | Template fait à la main, Python ne réécrit que les tables nommées ; test dans Excel 365 |
| Le code déborde sur J3 | Gel du code J2 au soir : ce qui n'est pas fini est coupé |
| Les 3 decks se ressemblent | Une décision différente par deck, validée avant d'écrire les slides |
| Le pipeline ne tourne pas sur une autre machine | Test depuis un `git clone` vierge J3 matin |

---

## 7. Critères de réussite

- [ ] `pip install -r requirements.txt` puis `python main.py` fonctionnent depuis un clone vierge
- [ ] Toutes les statistiques du classeur sont produites par le code
- [ ] « État des données » liste sources, écarts, corrections et exclusions avec leurs raisons
- [ ] L'outil Excel fonctionne sans macro (sélection ATC et période)
- [ ] La donnée publique est dans l'analyse et sert au moins une recommandation
- [ ] Le backtest compare chaque modèle aux baselines, avec un verdict par groupe
- [ ] Le mémo contient les 2 parties, avec une position tranchée sur le partage
- [ ] Les 3 decks portent 3 messages et 3 décisions différents
- [ ] Le README dit qui a fait quoi ; l'historique Git montre les deux contributions
- [ ] Aucun fichier inutile dans le dépôt
