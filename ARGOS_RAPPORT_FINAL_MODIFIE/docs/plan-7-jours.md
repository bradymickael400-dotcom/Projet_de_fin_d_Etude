# Programme d'exécution — construire ARGOS Intelligence puis soumettre

## Objectif concret à obtenir avant le dossier

À la fin de **J7**, ARGOS doit être une démonstration intégrée : une télémétrie réelle ou explicitement marquée **SIMULÉE** est ingérée, analysée, corrélée à un trajet et à des règles métier, puis transforme l'incident en recommandation sourcée soumise à une revue humaine. Chaque décision possède une trace d'audit.

Fonctions à livrer :

1. détection d'anomalies de télémétrie ;
2. estimation de risque et classification de gravité ;
3. réduction des faux positifs ;
4. analyse GPS, trajet et géorepérage ;
5. recommandations opérationnelles ;
6. agent ARGOS appuyé sur une base de connaissances ;
7. explication, incertitude et validation humaine ;
8. journal de décision traçable.

Une fonction n'est « livrée » que si ses entrées, sorties, test et limite sont documentés. Les règles de seuil existantes sont le filet de sécurité. Un modèle ML n'est intégré que si les données permettent de le tester honnêtement.

## Architecture de travail

```text
ESP32 ou simulateur étiqueté
  -> API IoT -> stockage événements/télémétrie
  -> moteur ARGOS Intelligence
     (qualité -> règles -> anomalie -> risque -> gravité -> trajet)
  -> recherche KB + agents Incident et Conformité
  -> recommandation + validation humaine
  -> journal d'audit + interface
```

Chaque analyse doit exposer : identifiant, événements concernés, origine `DEVICE|SIMULATED`, anomalies et preuves, niveau de risque/gravité, état trajet, données manquantes, recommandations, sources (document/URL/passage), incertitudes, version de règle/modèle et statut de revue humaine. Un score non calibré ne doit pas être présenté comme une probabilité. Les journaux conservent les faits et sources, jamais une chaîne de pensée interne.

---

## Jour 1 — Cadrer l'IA ARGOS et préparer les fondations

**But :** passer des intentions à un contrat technique et à des critères de succès.

1. Confirmer l'inscription, l'accès Sandbox et les crédits ; consigner le résultat sans l'inventer.
2. Choisir le pays et le domaine du corpus. Proposition : Cameroun et logistique de conteneurs. Sans choix, l'agent reste limité aux conseils techniques non réglementaires.
3. Choisir le scénario de référence : conteneur frigorifique, choc, porte ouverte, perte GPS, données contradictoires.
4. Cartographier le payload existant : température, humidité, choc, pression, porte, flamme, batterie, GPS, vitesse, qualité, séquence et horodatage.
5. Définir une taxonomie : incidents, niveaux `INFO/WARNING/CRITICAL`, actions autorisées et actions imposant une revue humaine.
6. Écrire le contrat de sortie unique de l'analyse et les responsabilités des rôles : moteur d'analyse, agent Incident, agent Conformité, opérateur humain.
7. Créer le backlog : analyse, données, KB, agents, journal, API, interface, sécurité, tests et rapport.

**Livrables :** dictionnaire de données, contrat JSON, scénario, taxonomie et backlog priorisé.

**Validation :** trois entrées (normale, alerte, données insuffisantes) produisent une sortie déterministe conforme au contrat.

**Durée :** 5–7 h. **Repli :** accès Sandbox absent → prototype local compatible, blocage documenté.

## Jour 2 — Construire les données et la base de connaissances

**But :** obtenir des données de démonstration reproductibles et des sources que l'agent peut citer.

1. Extraire des données non sensibles ou générer des séries **SIMULÉES** : normal, température élevée, choc, dérive GPS, batterie faible, mesures manquantes et doublons.
2. Étiqueter chaque événement : incident attendu, gravité, recommandation, scénario et origine.
3. Séparer développement, validation et démonstration ; ne jamais présenter une simulation comme une mesure terrain.
4. Collecter les documents officiels nécessaires. Pour chacun : titre, autorité, URL, date de consultation, version, langue, licence/statut et domaine.
5. Transformer en texte, découper en passages stables et garder document/page/section dans les métadonnées.
6. Indexer la KB vectorielle dans le Sandbox lorsque l'accès est effectif ; sinon utiliser un prototype local explicitement identifié.
7. Écrire dix requêtes de contrôle (incidents et conformité) avec le passage attendu.

**Livrables :** jeu de scénarios étiquetés, registre de provenance, corpus versionné, manifest d'ingestion, index et requêtes KB.

**Validation :** chaque requête retourne un passage pertinent avec URL ; un document sans provenance est refusé.

**Durée :** 7–9 h. **Repli :** source inaccessible → consigner l'absence et ne pas l'utiliser.

## Jour 3 — Implémenter le moteur d'analyse de télémétrie

**But :** produire anomalies, risque et gravité à partir d'événements validés.

1. Créer une interface de moteur : `analyze(telemetry_window, context) -> AnalysisResult`.
2. Contrôler la qualité : âge, séquence, GPS valide, bornes physiques, capteur indisponible et doublon. Une donnée douteuse crée une incertitude, pas une certitude.
3. Réutiliser les seuils existants comme règles de référence et exposer la règle déclenchée dans la sortie.
4. Corréler dans une fenêtre temporelle pour distinguer un pic transitoire d'un incident persistant.
5. Implémenter une matrice de risque : exposition, persistance, qualité de données et contexte de trajet ; conserver les facteurs actifs.
6. Mapper les résultats vers `INFO/WARNING/CRITICAL` dans une règle versionnée.
7. Examiner Isolation Forest : l'utiliser uniquement si assez de séries normales cohérentes existent. Sinon documenter son rejet. S'il est retenu : entraînement développement, prétraitement/version/seuil figés, comparaison aux règles et validation étiquetée.

**Livrables :** module d'analyse, règles versionnées, décision argumentée sur le ML et tests unitaires.

**Validation :** cas normal, choc isolé, choc persistant, température élevée, mesure invalide et doublon avec sorties attendues.

**Métriques :** précision/rappel/F1 seulement avec labels fiables ; sinon détection et faux positifs sur scénarios contrôlés, avec limite explicitée.

**Durée :** 7–9 h. **Repli :** modèle ML non justifié → baseline par règles.

## Jour 4 — Analyser le trajet et réduire les fausses alertes

**But :** compléter l'intelligence métier et fiabiliser les alertes.

1. Définir trajet prévu, géozones et tolérance. Sans référence, retourner `UNKNOWN`, jamais une fausse déviation.
2. Implémenter GPS : absence, précision insuffisante, vitesse incohérente, sortie de zone, arrêt anormal et déviation.
3. Réduire les faux positifs : persistance minimale, fusion de doublons, qualité capteur, corrélation multi-capteurs et confirmation opérateur.
4. Construire un registre de recommandations explicables : condition, action, niveau de risque et nécessité de revue.
5. Ajouter le feedback opérateur `true_alert|false_alert|unknown` avec commentaire ; c'est la future source de labels, pas encore un modèle entraîné.
6. Rejouer le scénario avec GPS absent et données contradictoires.

**Livrables :** analyse trajet/géozones, déduplication, recommandations et modèle de feedback.

**Validation :** quatre trajets synthétiques : conforme, déviation, GPS imprécis et GPS absent, plus une série d'alertes répétées.

**Durée :** 6–8 h. **Repli :** routage indisponible → géorepérage par coordonnées annoncé comme simplifié.

## Jour 5 — Construire l'agent ARGOS et le RAG sourcé

**But :** fournir un assistant de décision audit-able, sans lui donner le pouvoir d'agir seul.

1. Relier la décision structurée à la recherche KB ; retourner score, document, URL, section et version.
2. Créer l'agent **Incident** : il résume les faits d'`AnalysisResult` sans modifier les mesures ou scores.
3. Créer l'agent **Conformité** : il recommande conditionnellement en citant les passages. Sans source adéquate, il répond « information insuffisante ».
4. Ajouter l'orchestrateur déterministe : analyse → récupération → agents → résultat final, avec persistance des entrées/sorties.
5. Imposer la réponse : faits, données manquantes, interprétation, recommandation, sources, incertitudes et revue requise.
6. Interdire les actions physiques, disciplinaires ou légales automatiques.
7. Tester : injection documentaire, absence de source, source hors sujet, KB indisponible et données contradictoires.

**Livrables :** KB interrogée, deux rôles distincts, orchestrateur, prompts/versionnement et tests de citation.

**Validation :** chaque recommandation liée à une politique possède une source vérifiable ; une question sans source reçoit un refus prudent.

**Durée :** 7–9 h. **Repli :** LLM indisponible → réponses déterministes/gabarits avec mêmes sources et même audit trail, clairement indiquées.

## Jour 6 — Intégrer, sécuriser, journaliser et visualiser

**But :** relier les composants opérationnels et rendre chaque décision contrôlable.

1. Ajouter les structures de journal : analyse, événements, version règle/modèle, documents récupérés, recommandation, statut de revue, utilisateur et horodatage.
2. Ajouter une API sécurisée pour analyser une fenêtre et consulter l'historique ; vérifier les autorisations par rôle.
3. Connecter l'interface : chronologie, analyse, sources cliquables, incertitudes, décision humaine. Afficher `DEVICE` ou `SIMULATED` de façon visible.
4. Vérifier l'absence de secret dans les logs, UI, dépôt et captures.
5. Limiter CORS aux origines réelles et documenter les variables d'environnement.
6. Écrire les tests d'intégration : payload invalide, accès non autorisé, source absente, revue requise et écriture d'audit.

**Livrables :** API → intelligence → journal → interface, procédure d'exécution et note de sécurité.

**Validation :** un scénario affiche les faits d'entrée, la décision, les sources et le statut de revue ; un accès non autorisé est refusé.

**Durée :** 7–9 h. **Repli :** interface longue à modifier → page de démo isolée connectée à l'API, jamais une capture statique présentée comme temps réel.

## Jour 7 — Tester, mesurer et figer la solution démontrable

**But :** créer les preuves nécessaires avant tout rapport.

1. Redémarrer l'environnement par une procédure documentée et noter versions/dépendances.
2. Rejouer trois scénarios : normal, incident critique progressif, données incomplètes/contradictoires.
3. Archiver pour chacun : payloads, origine, analyse, passages KB, recommandations, revue humaine et journal d'audit.
4. Exécuter tests unitaires/intégration ; conserver commande, date, résultat, échec et correction.
5. Mesurer seulement ce qui est observé : latence, succès scénario, précision/rappel si labels fiables, faux positifs sur jeu synthétique. Décrire méthode et limites.
6. Réviser manuellement cohérence des recommandations, appui réel des sources et étiquetage des simulations.
7. Produire le tableau « annoncé / prouvé / limite » ; enlever toute fonction non prouvée de la présentation.

**Livrables :** rapport de tests, paquet de preuves, captures, résultats des scénarios et inventaire final.

**Critère de fin :** un tiers peut réinstaller, rejouer les trois scénarios et retrouver sources/décisions sans aide de développement.

**Durée :** 7–9 h. **Repli :** service externe échoue → démo locale de secours sur jeu synthétique et KB déjà indexée, explicitement déclarée.

---

## Jour 8 — Rédiger le dossier officiel depuis les preuves

**But :** remplir le modèle officiel uniquement avec ce qui a réussi à J7.

1. Utiliser le modèle officiel et sa limite de cinq pages, si elle est confirmée au moment du dépôt.
2. Présenter problème, utilisateurs et valeur en distinguant prototype, simulation et matériel vérifié.
3. Décrire le flux capteur/simulateur → API → IA → KB/agents → humain → audit.
4. Décrire chaque modèle réellement utilisé : règles, Isolation Forest seulement s'il a été retenu/testé, embeddings/LLM éventuels, données, métriques et limites.
5. Ajouter la matrice d'alignement exigences du concours, Y.3172 et AI Readiness ; écrire « alignement démontré », jamais « certifié conforme ».
6. Présenter scénarios, résultats, échecs, sécurité, gouvernance, provenance et revue humaine.
7. Ajouter sources officielles, lien dépôt, manifest KB et procédure de reproduction.

**Livrable :** version 1 professionnelle, factuelle, à cinq pages maximum hors annexes si autorisées.

**Validation :** chaque affirmation renvoie à une preuve de J7.

## Jour 9 — Corriger, figer et préparer la soumission

**But :** garantir que code, démonstration et document décrivent exactement la même solution.

1. Relire comme un évaluateur et retirer promesses, chiffres non mesurés et sources imprécises.
2. Corriger seulement les défauts bloquants révélés par la relecture.
3. Rejouer le scénario critique après chaque correction significative et mettre à jour la preuve affectée.
4. Contrôler les artefacts de soumission : rapport, dépôt, KB, éléments Sandbox et vidéo optionnelle.
5. Vérifier l'absence de secrets, mots de passe et données sensibles.
6. Finaliser la checklist : liens, versions, lancement, limites et responsable de validation humaine.
7. Faire valider humainement le paquet avant dépôt.

**Livrable :** paquet prêt à soumettre et démonstration de secours.

**Critère de fin :** dépôt, KB, rapport et démo ont les mêmes fonctionnalités et les mêmes limites.

## Dépendances à résoudre dès J1

- inscription/accès Sandbox et crédits ;
- décision sur le pays et les autorités sources ;
- accès au modèle ou choix du repli local ;
- localisation/restauration des tests absents de l'arbre inspecté ;
- autorisation de modifier le dépôt applicatif parent, hors de l'espace d'écriture actuel.
