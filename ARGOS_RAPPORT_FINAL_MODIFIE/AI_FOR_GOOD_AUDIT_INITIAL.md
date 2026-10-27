# ARGOS — audit initial AI for Good Lab Hackathon UAE

**Date d'audit :** 22 octobre 2026 (Africa/Douala)  
**Périmètre :** sources officielles accessibles, dossier `IAforgood`, code ARGOS accessible dans le dépôt parent, configuration Docker et firmware disponible.  
**Méthode :** une fonction n'est déclarée opérationnelle que lorsqu'elle est étayée par du code ou une exécution observée. Les documents de conception et le rapport sont traités comme des objectifs, non comme des preuves d'implémentation.

## A. Inventaire des sources

| Ressource | État | Utilisation dans l'audit |
|---|---|---|
| [Page officielle du hackathon](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/) | Consultée le 22-10-2026 | Règles, critères, livrables et calendrier. |
| [ITU-T Y.3172 (06/19)](https://www.itu.int/rec/T-REC-Y.3172-201906-I/en) | Consultée le 22-10-2026 ; en vigueur | Cadre architectural ML ; non assimilé automatiquement à une obligation réglementaire. |
| [AI Ready — Report 2.0](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf) | Consultée le 22-10-2026 ; copie locale disponible | Référentiel de préparation IA et de cartographie. |
| `IAforgood/AI-for-Good-Sandbox-Hackathon-submission-template.docx` | Lu | Modèle local de rapport, à adapter à ARGOS. |
| `IAforgood/From Connectivity to Intelligence UAE Capacity Building Week Program.pdf` | Lu | Guide pédagogique ; utile, mais pas un règlement du concours. |
| `IAforgood/2-exigences_lacunes_y3172_fr.docx` | Lu | Interprétation locale de Y.3172 ; à vérifier contre la recommandation officielle avant toute revendication. |
| `IAforgood/cas - pratique Agent de sécurité pour enfants plan d'évaluation du hackathon.docx` | Lu | Exemple de préparation ; il ne constitue pas une règle officielle. |
| `IAforgood/SKILL*.md` | Lu | Ressources de travail non officielles. Les procédures dépendantes de Claude, de GPU ou de modèles externes ne sont pas importées comme exigences ARGOS. |
| Dépôt ARGOS sous `/home/ar7mix/Documents/projet/pfe/pfe` | Inspecté en lecture | État technique réel. |

### Échéances et alertes

- L'inscription était annoncée ouverte jusqu'au **21 octobre 2026** ; à la date de cet audit, l'échéance est dépassée d'un jour. La FAQ précise que l'inscription initiale sert à recenser l'intérêt et que les données détaillées d'équipe arrivent plus tard. **Action P0 : contacter l'organisateur / vérifier son enregistrement immédiatement.**
- Date officielle de remise : **10 novembre 2026**.
- Premier tour : 11–18 novembre 2026 ; annonce des équipes présélectionnées : 18 novembre 2026.
- Équipe : maximum quatre personnes.

## B. Registre initial des exigences

| ID | Exigence | Source officielle et section | Nature | Preuve attendue | Priorité |
|---|---|---|---|---|---|
| R-01 | Construire et démontrer une solution **à base d'agents IA** utilisant une base de connaissances issue de documentation liée au cas d'usage. | Page officielle, « Requirements for Participants » | Obligatoire | Démo, code, KB, requêtes et réponses sourcées | P0 |
| R-02 | Mapper la solution aux politiques, lois, stratégies, normes et responsabilités institutionnelles pertinentes. | Page officielle, exigences 2 et 4 | Obligatoire | Corpus source, matrice de correspondance et citations | P0 |
| R-03 | Utiliser le code de référence ITU pour extraire, structurer et ingérer les documents dans une base de connaissances vectorisée distribuée hébergée dans l'AI for Good Lab. | Page officielle, exigence 3 | Obligatoire sous réserve d'accès au Sandbox | Dépôt/artefact d'ingestion et preuve d'exécution Sandbox | P0 |
| R-04 | Utiliser les crédits cloud Sandbox pour ajuster des modèles et créer un ou plusieurs agents. | Page officielle, exigence 4 | Obligatoire conditionnée à l'accès Sandbox | Preuve d'accès, configuration et résultats | P0 |
| R-05 | Créer un scénario d'erreurs interactif : événements séquencés, incomplets et répartis entre agents. | Page officielle, exigence 5 | Obligatoire | Scénario rejouable, logs et résultats attendus/observés | P0 |
| R-06 | Journaliser les décisions et les références de politiques afin qu'elles soient contrôlables. | Page officielle, exigence 6 | Obligatoire | Journal horodaté : entrées, sources, action, acteur, résultat | P0 |
| R-07 | Aligner l'architecture avec Y.3172 et l'AI Readiness Framework. | Page officielle, paragraphe suivant exigence 6 | Critère de notation | Tableau de correspondance justifié | P1 |
| R-08 | Qualité de la KB : complétude, exactitude, structure et capacité de récupération du contexte politique pertinent. | Page officielle, « Evaluation Criteria » | Critère de notation | Corpus, métadonnées, tests de recherche et citations | P0 |
| R-09 | Capacité des agents : pertinence et exactitude pendant les scénarios ; respect des lois, mandats et mécanismes de coordination. | Page officielle, « Evaluation Criteria » | Critère de notation | Cas de test, réponses, sources, validation humaine | P0 |
| R-10 | Identifier des lacunes de politiques/normes et des exemples globaux pertinents. | Page officielle, « Evaluation Criteria » | Critère de notation | Registre de lacunes, sources de pays et exemples internationaux vérifiés | P0 |
| R-11 | Soumettre : rapport technique de cinq pages maximum, dépôt GitHub, base de connaissances ; vidéo facultative de sept minutes maximum. | Page officielle, « Submission Materials » | Obligatoire | Fichiers et URL contrôlés | P0 |
| R-12 | Respecter l'honnêteté de la démonstration : le résultat réel est distingué du résultat simulé. | Inférence de la demande de démonstration et bonne pratique | Bonne pratique technique | Étiquetage clair des données et journal de tests | P1 |

### Statut des normes

Y.3172 est une recommandation ITU-T en vigueur, approuvée le 22 juin 2019. Elle définit un cadre d'architecture pour l'apprentissage automatique dans les futurs réseaux incluant IMT-2020 ; elle n'est pas, à elle seule, une certification de sécurité ou une loi applicable à ARGOS. Le concours demande un **alignement** ; il faut donc sélectionner et démontrer uniquement les aspects réellement mis en œuvre.

Le rapport AI Readiness 2.0 est un référentiel d'analyse. Il met notamment en avant données, infrastructure numérique, compétences, écosystème d'innovation et politique IA. Il sert à structurer le dossier, non à certifier la conformité d'ARGOS.

## C. État réel d'ARGOS

### Composants vérifiés

| Composant | État | Preuve inspectée |
|---|---|---|
| Ingestion IoT | Opérationnelle dans le code | `app/modules/iot/validator.py`, `iot_service.py`, `repository.py` : schéma JSON, bornes numériques, UUID, horodatage, séquence, authentification d'appareil. |
| Alerte de télémétrie | Partielle / à règles | `iot_event_service.py` : seuils température, humidité, choc, pression et vitesse ; notification. Aucun modèle ML identifié. |
| Stockage et temps réel | Opérationnel dans le code | PostgreSQL/TimescaleDB, Redis, persistance de télémétrie et événements dans `repository.py` ; `docker-compose.yml`. |
| Plateforme web | Opérationnelle dans le code ; HTTP 200 vérifié le 13-10-2026 | Flask, Gunicorn, Docker, routes dashboard et IoT. Une revalidation complète est requise avant soumission. |
| Firmware ESP32 | Disponible ; fonctionnement matériel non vérifié | `firmware/argos_esp32/argos_esp32.ino`. Il émet de la télémétrie, mais aucun journal matériel ni mesure terrain n'a été fourni durant cet audit. |
| Simulateurs | Disponibles | `simulateur_iot.py` et `scripts/simulate_argos_box.py` référencés dans le dépôt. Les données simulées doivent être marquées comme telles. |
| Assistant LLM | Partiel | `/api/ai/chat` utilise l'API Gemini avec un prompt de rapport ; un repli DeepSeek existe. Ce n'est pas une KB vectorielle ni un agent de politique. |
| Sécurité applicative | Partielle | Jetons signés, RBAC, clés appareil hachées et validation de payload sont présents. CORS permissif, valeurs d'environnement par défaut et absence de preuve de tests de sécurité restent des écarts. |
| Tests automatisés | Non vérifiables dans l'arbre de travail actuel | Les répertoires `tests/` et `docs/` sont absents du disque alors que Git les signale comme supprimés/ajoutés différés. Aucun test n'a été exécuté ici. |

### Audit d'ARGOS Intelligence

| Fonction demandée | État actuel | Preuve / limite | Travail nécessaire |
|---|---|---|---|
| Détection d'anomalies | Partielle : règles de seuil | Alertes configurées dans `iot_event_service.py` ; aucun Isolation Forest, entraînement, jeu de données ou évaluation trouvé. | Stabiliser les règles ; ajouter seulement un modèle si des données étiquetées ou une définition de normalité le justifient. |
| Estimation de risque | Absente | Aucun modèle de risque ou sortie probabiliste identifiée. | Définir cible, données et métrique ; ne pas revendiquer cette capacité avant test. |
| Gravité | Partielle | Les notifications utilisent une gravité critique, sans classifieur multi-niveaux vérifié. | Formaliser niveaux, règles, justification et validation humaine. |
| Réduction des faux positifs | Absente | Aucun mécanisme de retour opérateur ou modèle supervisé identifié. | Créer un statut de revue humaine et collecter les labels. |
| Analyse de trajets | Partielle | GPS, positions et interface cartographique sont présents ; aucun détecteur de détours/comportements inhabituels n'a été identifié. | Définir itinéraires, géorepérage et scénarios de déviation. |
| Recommandation d'actions | Partielle, non gouvernée | Gemini peut produire du texte à partir d'un contexte fourni par le client. Aucune récupération de sources ni politique déterministe n'est visible. | Ajouter règles vérifiables et agent de conseil fondé sur une KB citée. |
| Explication et sources | Absente pour l'IA | Aucun identifiant de document, extrait, score, version de modèle ou justification structurée dans la route Gemini. | Journal de décision avec preuves, références et statut de revue. |
| Journalisation de décisions IA | Absente | Des journaux d'audit IoT existent, mais pas de trace dédiée aux décisions, outils et sources d'un agent. | Ajouter un schéma `agent_decisions` et des traces sûres orientées preuve, pas des raisonnements internes bruts. |

## D. Matrice des écarts

| Exigence | État réel | Écart et conséquence | Priorité | Action corrective / critère de validation |
|---|---|---|---|---|
| R-01 Agent + KB | Assistant Gemini externe seulement | Risque majeur de non-adéquation au thème. | P0 | Implémenter un agent ARGOS Policy & Incident avec outils strictement définis et KB locale/ITU ; réponse toujours accompagnée de sources. |
| R-02 Corpus de politiques | Aucun corpus national/sectoriel ARGOS trouvé | Aucune base pour conseiller sur une décision ou identifier une lacune. | P0 | Choisir le pays et le domaine institutionnel ; collecter les textes officiels avec URL, date, licence et métadonnées. |
| R-03 KB vectorisée / code ITU | Absente | Livrable explicite manquant. | P0 | Obtenir l'accès Sandbox et exécuter/adopter le code ITU de référence ; sinon documenter le blocage et préparer un prototype local compatible. |
| R-04 Crédits Sandbox | Non vérifiable | Accès et capacité à ajuster un modèle non prouvés. | P0 | Vérifier l'admission, les crédits et les conditions d'utilisation. |
| R-05 Scénario séquencé multi-agent | Absent | La démonstration actuelle IoT ne répond pas au scénario de politique distribué. | P0 | Construire un scénario ARGOS de rupture de scellé / détérioration / partage de données avec événements progressivement libérés. |
| R-06 Auditabilité d'agent | Absente | LLM non attribuable, donc faible score sur auditabilité. | P0 | Log structuré : ID scénario, entrée, sources récupérées, règle/politique, recommandation, superviseur, horodatage et version. |
| R-08 Qualité KB | Absente | Critère de notation non démontré. | P0 | Jeux de requêtes de récupération avec passages attendus et citations. |
| R-09 Capacité d'agent | Absente | Le chat générique ne démontre ni rôle institutionnel ni coordination. | P0 | Démontrer au minimum deux rôles : agent opérationnel ARGOS et conseiller conformité/politique ; garder un arbitre humain. |
| R-10 Lacunes et exemples globaux | Absente pour ARGOS | Point évalué explicitement, donc risque fort de mauvaise note. | P0 | Produire un registre de lacunes sourcées : données maritimes, responsabilité des alertes, localisation, décisions automatisées, interopérabilité. |
| R-11 Rapport, GitHub, KB | Rapport PFE disponible mais format concours non établi ; GitHub/KB non vérifiables | Soumission potentiellement incomplète. | P0 | Produire un rapport de 5 pages dans le modèle, vérifier dépôt public/partiel et empaqueter KB. |
| Validation automatisée | Tests absents dans l'arbre présent | Démonstration non reproductible. | P1 | Restaurer/écrire tests ciblés ; conserver commandes et résultats. |
| Sécurité de démo | Partielle | Valeurs par défaut dans Compose et CORS `*`; ne pas exposer publiquement sans durcissement. | P1 | Retirer valeurs par défaut faibles, vérifier `.env` ignoré, limiter origines, effectuer test d'autorisation. |

### Bilan

**Forces vérifiées :** chaîne IoT structurée, validation rigoureuse des payloads, authentification d'appareils, persistance PostgreSQL/Redis, architecture Docker démontrable et interface de supervision.

**Différenciateur réaliste :** ARGOS peut devenir un cas d'usage de logistique maritime intelligente où l'agent fait le lien entre événements physiques et obligations/politiques, au lieu d'être un simple chatbot ou un simple traceur.

**Lacune dominante :** le dossier actuel est orienté IoT et télémétrie, tandis que le concours est orienté agents, base de connaissances nationale, scénarios de politique et lacunes de normes. Il faut recentrer la candidature sur ce second axe sans prétendre que les fonctions IoT envisagées sont toutes déployées.

## E. Architecture cible minimale pour la candidature

```text
ESP32 ou simulateur étiqueté
        -> API IoT ARGOS -> PostgreSQL / événements
                                 |
                         Scenario Orchestrator
                           |              |
                  Agent opérationnel   Agent conformité
                   (lecture événement)  (RAG sur KB)
                           \              /
                    Décision structurée + revue humaine
                                 |
               Journal d'audit, citations, UI de démonstration
```

Le premier MVP doit être **simple** : deux agents à rôles distincts, une KB de documents officiels, une orchestration déterministe, des citations obligatoires et une recommandation que l'humain confirme ou rejette. Il ne faut pas entraîner un modèle de télémétrie faute de données étiquetées : les règles existantes constituent une base plus démontrable à court terme.

## F. Plan de sept jours (calendrier provisoire)

| Jour | Objectif et livrable | Critère de fin |
|---|---|---|
| J1 | Confirmer l'inscription et l'accès Sandbox ; figer pays, domaine et scénario ; créer registre de sources. | Accès ou blocage documenté ; au moins un corpus de sources officielles identifié. |
| J2 | Stabiliser l'exécution ARGOS et tracer une télémétrie réelle ou explicitement simulée ; restaurer/écrire tests ciblés. | Parcours reproductible capteur/simulateur → API → base → UI avec journal. |
| J3 | Construire la KB et l'ingestion compatible avec la référence ITU ; ajouter métadonnées et tests de récupération. | Chaque réponse de test retourne une source et un extrait vérifiables. |
| J4 | Implémenter agents, orchestration et journal de décision ; définir les rôles et les limites. | Deux agents produisent des sorties structurées et auditables. |
| J5 | Construire puis rejouer le scénario séquencé ; tester erreur, conflit de recommandations et revue humaine. | Journal complet des événements, sources, décisions et interventions humaines. |
| J6 | Durcir la démonstration, mesurer ce qui est réellement mesurable, rédiger rapport de cinq pages et matrice Y.3172/Readiness. | Aucun résultat non sourcé ; rapport conforme au modèle. |
| J7 | Rejouer depuis une installation propre ; préparer dépôt GitHub, KB, vidéo facultative et checklist de soumission. | Artefacts accessibles, démonstration répétable, validation humaine finale. |

## G. Décisions immédiates

1. **P0 — Confirmer l'éligibilité / inscription et l'accès au Sandbox.** Sans cet accès, R-03 et R-04 restent bloqués.
2. **P0 — Choisir le pays dont les politiques alimenteront la KB.** ARGOS est camerounais, mais le concours demande des politiques de pays : le choix doit être explicite et juridiquement défendable.
3. **P0 — Valider le scénario de concours proposé :** incident de conteneur progressif, divergence entre continuité logistique et protection des données, puis recommandation avec références.
4. **P1 — Restaurer ou localiser le dossier de tests et la documentation supprimés dans l'arbre de travail avant toute modification large.**
5. **P1 — Ne pas exposer l'instance publique actuelle avec des secrets ou identifiants par défaut.**

## Références

1. ITU AI for Good, *AI for Good Lab Hackathon: United Arab Emirates*, consulté le 22 octobre 2026 : https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/
2. ITU-T, *Recommendation Y.3172 (06/19): Architectural framework for machine learning in future networks including IMT-2020*, statut en vigueur, consulté le 22 octobre 2026 : https://www.itu.int/rec/T-REC-Y.3172-201906-I/en
3. ITU, *AI Ready – Analysis Towards a Standardized Readiness Framework, Report 2.0*, janvier 2026 : https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf
