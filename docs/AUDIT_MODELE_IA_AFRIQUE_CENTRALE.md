# Audit ARGOS et trajectoire vers une IA exploitable en Afrique centrale

**Date de l’inspection : 29 octobre 2026**  
**Périmètre :** dépôt logiciel présent, prototypes de données, services IoT, agents, calcul d’ETA, configuration de déploiement et preuves documentées. Cet audit statique n’est ni un audit de sécurité indépendant ni une validation sur le terrain. Aucun test n’a été lancé pour cet audit.

## Correctifs appliqués après l’audit

- État sécurité : une table d’état persistant conserve les modes souhaités, rapportés et en attente de confirmation; un endpoint de commande autorisé écrit le réglage et publie une commande ESP32; la télémétrie confirme l’application du réglage. L’interface réutilise l’état renvoyé par le profil après rechargement.
- Rejeu : `stream_transport_scenario.py` et `replay_demo_transport_dataset.py` transmettent la provenance synthétique, l’identifiant du jeu, du scénario et l’étiquette simulée. Les événements qui en résultent restent des relectures et ne sont jamais présentés comme des mesures terrain.
- Carte superadmin : l’inventaire des boîtes actives est affiché même sans GPS récent; l’activation des traces demande les historiques et routes configurées pour cet inventaire. Les marqueurs GPS exposent le caractère synthétique des relectures.

Ces changements améliorent la persistance et l’observabilité. Ils ne créent pas de données terrain, ne réentraînent pas automatiquement le classifieur et ne suffisent pas à déclarer la collecte/validation régionale terminée. Sans trajets réels étiquetés et heures d’arrivée constatées, fabriquer un modèle terrain serait une affirmation non étayée.

## Verdict

ARGOS est aujourd’hui une application de suivi logistique avec ingestion IoT, règles d’alerte, services de position et de route, agents spécialisés et assistant LLM. Le dépôt contient aussi un premier modèle statistique effectivement entraîné par un script. Il n’est toutefois pas intégré au traitement opérationnel et il a été entraîné uniquement sur des relectures synthétiques. Le code ne démontre donc pas encore un modèle d’IA prédictif fiable en exploitation en Afrique centrale.

La base la plus crédible pour avancer est déjà présente : collecte et normalisation de télémétrie, identifiants d’appareils, positions horodatées, associations boîte-conteneur, routes planifiées, règles de détection explicables et une première chaîne d’entraînement/évaluation de démonstration. Le principal manque est la preuve terrain : données réelles avec provenance et qualité documentées, événements confirmés, comparaison à des références simples, essais prospectifs et processus de mise à jour contrôlé.

Il ne faut pas fusionner tous les usages dans un « modèle complet » unique. Détection d’incident, estimation du risque futur et estimation d’arrivée ont des cibles et des données d’évaluation différentes. Un LLM peut expliquer les résultats et aider à naviguer les procédures, mais ne doit pas être la source d’un score de risque ou d’une décision de sécurité.

## Ce que le dépôt démontre

| Domaine | État constaté | Preuve et portée |
|---|---|---|
| Ingestion IoT | Présente | `app/modules/iot/validator.py`, `iot_service.py`, `repository.py` valident le message, l’appareil, l’association et la séquence; `normalizer.py` neutralise les mesures signalées invalides. Cela prouve un chemin logiciel, pas la fiabilité du matériel en transport réel. |
| Protection d’accès | Partielle et significative | Jetons d’enrôlement et clés d’appareil hachés (`app/modules/iot/security.py`); les agents opérationnels vérifient les boîtes visibles (`app/agents/specialists.py`) et l’orchestrateur borne les outils aux boîtes sélectionnées (`app/agents/orchestrator.py`). Une revue complète des routes, privilèges, configuration et déploiement demeure nécessaire. |
| Alertes de capteurs | Présentes, fondées sur des règles | Seuils et conditions de déclenchement dans les services IoT et risque. Elles peuvent être utiles sans ML, mais un seuil configurable n’est pas une probabilité d’incident apprise. |
| Agents | Présents comme fonctions spécialisées | Le registre et les handlers incluent télémétrie, GPS/route, risque, recherche documentaire et capacités de transport/port (voir `app/agents/registry.py` et `specialists.py`). Leur présence ne prouve ni autonomie ni exactitude métier. Plusieurs résultats sont des lectures de service ou règles déterministes. |
| LLM externe | Intégration réelle dans le code; disponibilité non garantie | `app/llm/gemini.py` envoie le message et les résultats d’outils au fournisseur Google configuré. Les documents de preuve notent un HTTP 503 lors d’un appel antérieur et des tests au transport simulé. Vérifier contrat, région, journalisation, conservation et transferts avant d’y envoyer des données opérationnelles. |
| Modèle d’anomalie | Entraîné, expérimental, non opérationnel | `scripts/train_demo_anomaly_model.py` produit une régression logistique binaire v2 sur les jeux synthétiques de rejeu. `docs/INVENTAIRE_AGENTS_MODELES.md` confirme que l’application ne charge pas l’artefact pour ses alertes. |
| Données du modèle | Synthétiques seulement | `datasets/argos_demo_two_routes.json` (240 points) et `datasets/argos_central_africa_60min.json` (61 points), soit 301 observations sur cinq scénarios : 216 stables et 85 anomalies simulées. L’inventaire documentaire régional fourni par l’équipe n’est pas un jeu de lignes d’entraînement. |
| Validation du modèle | Très préliminaire | Validation laissant un scénario entier de côté; accuracy moyenne 87,37 %, précision 100 %, rappel 55,29 %. Ces chiffres mesurent l’accord avec des étiquettes générées par simulation, pas une performance terrain ni une probabilité calibrée. Le rappel varie de 20 % à 77,27 %, ce qui montre une forte variation entre scénarios. |
| ETA | Heuristique transparente | `app/services/route_intelligence_service.py` projette la position sur les segments planifiés et divise la distance restante par la médiane de jusqu’à six vitesses GPS récentes. Une position de plus de 20 minutes est rejetée; les arrêts, trafic, pluie, contrôle routier, douane, attente portuaire, ferry/transbordement et état de réseau ne sont pas prédits. Pas d’apprentissage sur les heures d’arrivée réelles. |
| Historique et carte | Services présents, disponibilité réelle à confirmer | Le suivi lit positions, mesures et événements depuis PostgreSQL; les documents antérieurs indiquent qu’aucune position exploitable n’était présente lors d’une capture. API présente ne veut pas dire historique alimenté ni couverture des boîtes sur une base déployée. |
| Déploiement | Conteneurisé, mais paramètres par défaut inadaptés à l’exposition | `docker-compose.yml` contient des valeurs de repli prévisibles pour mot de passe BD, secret d’application et compte admin, et configure un tunnel public de démonstration. `firmware/argos_esp32/README.md` documente un AP ESP32 ouvert et une clé locale par défaut. Ce sont des valeurs/documentations à remplacer et vérifier avant toute exploitation publique. |
| Gouvernance des données | Partielle, décisions organisationnelles à établir | Journal IA réduit et sans question brute dans `app/agents/audit.py`; pas de politique complète de conservation/suppression/transfert, jeu de labels ou accords de partage démontrés par ce code. L’accès autorisé n’établit pas à lui seul la conformité de l’usage secondaire pour l’entraînement. |

## Limites et manques déterminants

### 1. Les labels ne décrivent pas encore la réalité opérationnelle

Le script définit la cible comme `event != stable`. Dans les données disponibles, les anomalies sont simulées par scénario. Il n’existe pas, dans le dépôt inspecté, de preuve que chaque incident soit confirmé par un opérateur, une inspection, un rapport de transporteur ou une issue mesurée. Entraîner sur ces étiquettes apprend surtout les règles qui ont fabriqué les simulations. La validation par scénario ne remplace pas une séparation par expédition, appareil, période et corridor lorsque les données sont terrain.

Il manque aussi une taxonomie opérationnelle : choc bénin/sévère, ouverture autorisée/non autorisée, excursion thermique avec durée et type de marchandise, panne capteur, perte de position, retard observé, cause du retard et résultat final. Un label binaire « anomalie » mélange des événements qui n’ont ni le même coût ni la même réponse.

### 2. La cible ETA ne peut pas être jugée sur la vitesse seule

La formule actuelle est une bonne baseline explicable lorsque la route et la position sont fiables. En Afrique centrale, un temps d’arrivée dépendra aussi du mode de transport, de l’état et du type de route, des arrêts, du passage frontière, des horaires de terminal, des saisons et pluies, de la couverture GPS/cellulaire et de la qualité de l’heure de départ/arrivée. Le dépôt ne démontre pas que ces variables sont capturées ni que les heures d’arrivée observées sont enregistrées. Ne pas annoncer une ETA « prédictive » tant qu’elle n’est pas évaluée par corridor et mode; conserver l’heuristique avec son niveau de fraîcheur et une plage d’incertitude.

### 3. Les sources et instruments ne sont pas encore caractérisés terrain

Le validateur accepte des unités et bornes de format; le firmware décrit des capteurs prototypes et certaines valeurs estimées ou indisponibles. Il manque un registre de capteur et de calibration (modèle, numéro, montage, fréquence, dérive, dernière vérification), ainsi que des règles pour les données manquantes, horloges fausses, GPS imprécis, doublons, coupures réseau et changements de firmware. Une valeur numériquement valide n’est pas forcément une mesure physiquement fiable.

### 4. Le système d’exploitation IA n’est pas complet

Le modèle n’est pas servi par l’application. Aucun registre versionné complet entraînement–données–métriques–approbation–déploiement, surveillance de dérive, mécanisme de retour arrière ou processus de réentraînement reproductible n’est démontré. Les docs d’inventaire contiennent des constats historiques contradictoires (par exemple modèle « absent » dans la première partie et inventaire mis à jour dans la dernière). Il faut choisir une page de référence et dater chaque statut.

### 5. Le LLM et les règles ont des rôles différents

Gemini est un service externe qui reçoit le message de l’utilisateur et des résultats d’outils lorsque ceux-ci sont invoqués. Le LLM peut se tromper, être indisponible ou reformuler un résultat. Il ne doit ni remplacer l’autorisation côté serveur ni décider seul d’une alerte urgente, d’une conformité juridique ou d’une ETA. Prévoir une réponse déterministe de repli, minimiser les données envoyées et afficher les sources, date, fraîcheur et méthode.

### 6. Sécurité et gouvernance bloquent l’exposition en production

Les contrôles d’accès et l’authentification IoT constituent une base, mais les replis faibles du Compose, le tunnel de démonstration et l’AP de configuration ouvert rendent la configuration de démonstration impropre à une exposition telle quelle. Il faut aussi établir rotation/révocation des secrets, TLS et validation de certificats côté appareil, isolation réseau, sauvegardes restaurées en exercice, mises à jour firmware signées, limites de débit et surveillance d’incidents. La documentation d’audit indique que l’évaluation organisationnelle complète de conservation et de transferts est encore ouverte.

### 7. L’applicabilité régionale doit se mesurer corridor par corridor

« Afrique centrale » n’est pas un profil statistique unique. Route terrestre, port, transport maritime, pays, frontière, langue, climat, opérateur réseau et équipement changent la distribution des données. Les deux corridors simulés du dépôt ne prouvent pas une représentativité régionale. Il faut des partenariats terrain pour documenter les parcours effectivement exploités, les règles métier locales et les différences de qualité de service, sans présumer une couverture homogène.

## Architecture cible recommandée

1. **Acquisition robuste :** conserver les mesures brutes avec provenance et qualité; ajouter identifiant d’expédition, mode, corridor, identifiant/calibration capteur, version firmware, temps appareil et serveur, source GPS, précision, connectivité et événements métier. Prévoir stockage local chiffré et synchronisation idempotente après coupure.
2. **Contrôles déterministes :** garder les alarmes physiques urgentes, limites légales/configurées, qualité de capteur, géorepérage et validations dans les règles. Ces chemins doivent fonctionner sans Gemini et sans réseau externe.
3. **Modèles spécialisés :** (a) classification/triage d’incident avec classes utiles aux opérations; (b) estimation d’ETA par mode et corridor, avec plage P50/P90; (c) à terme seulement, risque d’événement dans un horizon défini. Commencer par des baselines simples comparées aux règles et à l’ETA actuelle; choisir un modèle tabulaire interprétable avant un modèle séquentiel complexe.
4. **Service d’inférence contrôlé :** charger un artefact versionné, vérifier schéma et fraîcheur, retourner résultat, version, raisons principales, limites et horodatage. En cas de données insuffisantes, sortir « estimation indisponible », jamais une confiance inventée. Le score appris reste une aide à la décision et les alarmes de sécurité restent sous règles validées.
5. **Assistant :** utiliser le LLM pour expliquer le résultat déjà calculé, citer les sources opérationnelles autorisées et traduire/résumer. L’assistant ne peut ni créer une observation ni rehausser la confiance statistique.
6. **Cycle de vie :** conserver manifeste du dataset et des labels, code/version, paramètres, métriques par tranche, validation humaine, approbation, déploiement progressif, surveillance, arrêt/retour arrière et historique de changement.

## Plan de réalisation avec critères de passage

### Phase A — Fermer les risques de démonstration et instrumenter (P0)

- Remplacer tous les secrets et mots de passe de repli; refuser le démarrage en mode production si des valeurs de développement sont présentes. Fermer ou protéger l’AP ESP32, retirer les clés par défaut et appliquer TLS avec validation de certificat sur les connexions appareil–serveur.
- Définir propriétaire, finalité, accès, durée de conservation, suppression, partage, localisation et fournisseur pour chaque catégorie de données. Faire valider les obligations par pays/corridor avant ingestion à grande échelle ou envoi au LLM.
- Écrire un dictionnaire de données et taxonomie d’incidents versionnés; enregistrer qualité et provenance sans convertir une valeur de secours en mesure observée.
- Mettre en place la file locale/synchronisation des télémétries hors ligne, l’idempotence, les horloges, les diagnostics et les statuts de capteurs. Tester sur le matériel et les réseaux réellement utilisés.
- Réconcilier `docs/INVENTAIRE_AGENTS_MODELES.md`, `docs/LIMITES_CONNues.md` et `docs/VERIFICATION_FONCTIONNALITES_IA.md` avec un tableau unique « présent / testé simulé / testé terrain / non vérifié ».

**Porte de sortie :** déploiement de test sans secrets par défaut; un parcours appareil→stockage→carte/alerte reproductible; données manquantes et appareil hors-ligne clairement signalés; responsables et règles de gouvernance documentés.

### Phase B — Constituer un jeu de données terrain fiable (P0)

- Démarrer avec un pilote limité à un ou deux corridors réels et modes explicitement choisis (par exemple un parcours routier camerounais et, si partenaire disponible, un parcours portuaire/maritime). Ne pas amalgamer les modes.
- Enregistrer des trajectoires complètes y compris trajets sans incident, attentes, retards, pertes de signal et changements de capteur; recueillir l’heure de départ/arrivée réelle et la cause lorsque connue.
- Faire confirmer les labels par des opérateurs selon une procédure écrite; conserver auteur, date, preuve et degré d’incertitude. Séparer incident observé, suspecté, simulé et inconnu.
- Contrôler droits d’usage, minimisation des identifiants, accès au jeu, rétention, anonymisation/pseudonymisation et mécanisme de retrait/correction.

**Porte de sortie :** chaque cible d’entraînement a une définition mesurable, un protocole de labellisation, un historique de provenance et une mesure publiée de couverture/qualité par corridor, appareil, capteur et classe. Le volume requis est déterminé par la précision statistique et le coût d’erreur visés; un nombre fixe de lignes ne suffit pas.

### Phase C — Modèles séparés, évaluation honnête (P1)

- **Incidents :** garder les règles comme baseline; entraîner un classifieur tabulaire par famille d’incidents si les exemples confirmés le permettent. Évaluer rappel par classe, précision, faux positifs par boîte/jour, délai d’anticipation, PR-AUC et calibration; choisir les seuils selon le coût d’alarme manquée et de fausse alerte.
- **ETA :** garder `distance / vitesse` comme baseline; entraîner un modèle de temps restant seulement après collecte d’arrivées réelles, avec segments/corridors et mode. Mesurer erreur absolue médiane, MAE, P90 et couverture de l’intervalle annoncé; comparer à la baseline par route, saison, pays et niveau de fraîcheur.
- **Séparation :** couper par expédition/voyage et période, jamais par lignes GPS aléatoires d’un même trajet. Ajouter un test sur corridor ou période jamais vu et un jeu final verrouillé. Répéter l’évaluation par appareil, type de conteneur, marchandise, mode, pays et qualité de signal.
- Rapporter intervalles d’incertitude et nombres d’exemples; une métrique sans support, intervalle ni base de comparaison n’est pas une preuve suffisante. Les labels synthétiques restent des tests d’intégration et sont exclus des métriques terrain.

**Porte de sortie :** le modèle bat la baseline sur une période/corridor tenu à l’écart, dans les seuils opérationnels décidés avec les utilisateurs; les performances, échecs et cas de refus sont audités et reproductibles.

### Phase D — Déploiement progressif (P1 puis P2)

- Déployer d’abord en mode silencieux (shadow), sans déclencher d’action, et comparer aux décisions/arrivées constatées. Ensuite, pilote assisté sur un seul corridor avec opérateur humain et possibilité d’ignorer/corriger.
- Afficher pour chaque résultat : « déclencheur » en langage clair, mesures sources, fraîcheur GPS/capteur, trajet utilisé, estimation et intervalle, version du modèle, raisons principales et bouton de retour opérateur.
- Surveiller couverture et retard de données, dérive, calibration, faux positifs, faux négatifs confirmés, erreurs par corridor et pannes. Suspendre automatiquement l’inférence apprise si schéma, distribution ou disponibilité franchit des seuils convenus; revenir à règles + estimation baseline.
- Après preuve sur plusieurs périodes et conditions saisonnières, étendre corridor par corridor avec validation locale; maintenir Français/Anglais et ajouter les langues opérationnelles nécessaires au périmètre choisi.

**Porte de sortie :** critères convenus avant le pilote, performance observée sur données prospectives, support humain disponible, retour arrière exercé, documentation et responsabilité opérationnelle attribuées.

## Indicateurs à publier pour une affirmation crédible

| Fonction | Mesures minimales |
|---|---|
| Qualité du flux IoT | couverture par capteur, taux d’échantillons invalides/manquants, retard et durée de perte de signal, doublons/rejeu, disponibilité GPS et précision, batterie, versions matérielles/firmware |
| Alertes d’incident | nombre confirmé par classe, précision/rappel avec intervalle, faux positifs par boîte/jour, délai d’alerte, résultats ventilés par corridor/marchandise/appareil; comparaison règles seules vs règles + modèle |
| ETA | erreur médiane/MAE/P90, biais en avance/en retard, couverture P50/P90, baseline actuelle vs modèle, ventilations par mode/corridor/étape et fraîcheur des données |
| Exploitation | disponibilité, latence p50/p95, coût par boîte/jour, part des résultats « indisponible », incidents de sécurité et temps de rétablissement |
| Gouvernance | provenance et droits des données, taux de labels revus, demandes de correction/suppression, accès et transferts documentés, durée de conservation effective |

## Standards et contexte régional

Utiliser le **NIST AI RMF** comme grille volontaire de gouvernance du cycle de vie (cartographier, mesurer et gérer les risques; vérifier la version courante car le NIST indique que la 1.0 est en révision), et la **Stratégie continentale de l’IA de l’Union africaine** comme référence de contexte africain pour les capacités, données, inclusion, coopération et gestion responsable des risques. Le document **ITU AI Ready** met en évidence des dimensions très concrètes pour un pilote régional : qualité/représentativité/étiquetage des données, gouvernance, connectivité, équipements, compétences, contextualisation et accès local. Ces cadres ne certifient pas ARGOS et ne remplacent pas une revue des lois applicables dans chaque pays.

- Union africaine, [Stratégie continentale de l’intelligence artificielle](https://au.int/en/documents/20240809/continental-artificial-intelligence-strategy).
- NIST, [AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) (page officielle; version 1.0 en révision au moment de l’inspection).
- ITU, [AI Ready – Analysis Towards a Standardized Readiness Framework](https://www.itu.int/epublications/publication/ai-ready-analysis-towards-a-standardized-readiness-framework).

## Conclusion opérationnelle

ARGOS a une base produit et un pipeline de démonstration ML, pas encore un modèle prédictif prêt pour les opérations régionales. Le livrable à viser n’est pas un modèle unique « complet », mais un système hybride : règles embarquées fiables pour les événements immédiats, modèle d’incident évalué sur des incidents confirmés, ETA spécialisée évaluée sur arrivées réelles, fonctionnement tolérant aux coupures, et assistant qui explique sans prendre la décision à la place des opérateurs. Le passage au terrain dépend d’abord des données, de la calibration des capteurs, de la sécurité de déploiement et d’un pilote mesuré sur des corridors réels.
