# Audit préalable — simulateur terrestre ARGOS

Date : 29 octobre 2026. Cet audit précède l'implémentation du simulateur.

## Architecture et flux existants

- **Backend / persistance :** Flask, PostgreSQL, SQLAlchemy; migrations SQL versionnées sous `migrations/` et exécutées par `app/migrate.py`.
- **Boîtes et droits :** `boite_noir`, `conteneurs`, `iot_devices`, `black_box_devices`; `GET /api/black-boxes/my-boxes` retourne les boîtes autorisées au profil. Les routes gestionnaires appliquent le périmètre de visibilité.
- **Télémétrie réelle :** `POST /api/iot/telemetry` valide un message, authentifie la clé du dispositif et la liaison boîte/conteneur, puis écrit mesures et positions, évalue les seuils, les notifications, le risque, les géorepères et les écarts d'itinéraire.
- **Contrat IoT vérifié :** `messageId` UUID, `type="telemetry"`, `deviceUid`, `blackBoxId`, `timestamp` ISO-8601 UTC, `sequence`, objets `position`, `sensors` et `modes`; la position exige latitude, longitude, précision, vitesse et cap. Les mesures exigent notamment température, humidité, choc, pression, flamme, porte et batterie; les quatre états `modes` sont obligatoires. `quality` porte `dataOrigin` (`FIELD`/`SYNTHETIC`) et l’identifiant/étiquette de scénario. Le backend vérifie aussi le lien actif dispositif–boîte et la séquence. Bien que ce contrat accepte une provenance synthétique, l’ingestion existante produit des mesures, événements et notifications opérationnels; le simulateur ne l’appelle donc pas.
- Les lots de simulation sont construits avec ce contrat, validés localement par `validate_telemetry_payload`, conservés pour audit avec `dataOrigin=SYNTHETIC`, et ne sont jamais soumis à l’endpoint d’ingestion. Leur `deviceUid` synthétique ne détient pas de clé active.
- **Pont Wi-Fi direct :** `POST /api/black-boxes/{id}/direct-telemetry` est authentifié par profil mais alimente le même stockage opérationnel et peut déclencher des notifications/e-mails. Il ne convient pas au simulateur.
- **Routes :** `argos_planned_routes` et `PUT /api/black-boxes/{id}/planned-route` enregistrent une route sur la boîte opérationnelle. Le moniteur calcule un écart géométrique et crée des notifications persistantes avec une fenêtre de déduplication de 30 minutes.
- **ETA :** calcul déterministe sur distance restante et médiane des vitesses GPS récentes. Les arrêts, files, météo et trafic ne sont pas modélisés; une position trop ancienne ou une vitesse nulle rend l'estimation indisponible/arrêtée.
- **Carte / rafraîchissement :** Leaflet; positions, boîtes et trajets sont lus depuis les API existantes. La carte interroge les données environ toutes les 10 secondes; aucun flux SSE/WebSocket de suivi n'est utilisé par cet écran.
- **Routage :** l'interface appelle déjà le service public `router.project-osrm.org` pour afficher une route; il n'existe pas de service backend de géocodage/routage poids lourd. OSRM public ne fournit pas à ARGOS une ETA trafic temps réel ni la validation des restrictions camion.
- **IA et alertes :** le moteur en place comprend des agents enregistrés/orchestrés (`iot_monitor`, `gps_route`, `risk_assessor`, `knowledge_retriever`, ainsi que les capacités de données Afrique centrale, ports et réglementation), des règles déterministes et un classifieur expérimental séparé. Le classifieur de démo décrit dans `docs/INVENTAIRE_AGENTS_MODELES.md` n'est pas chargé par l'application; ses métriques synthétiques ne sont pas des résultats terrain. Les alertes opérationnelles sont persistées depuis le pipeline IoT ou certaines routes d'assistance. Le simulateur réutilise uniquement les fonctions de règles sans effet secondaire et conserve ses évaluations dans le stockage isolé; il n'appelle ni Gemini ni les agents de lecture de télémétrie réelle sur de fausses mesures.

## État constaté dans la base locale

Deux boîtes non archivées sont enregistrées : `#1` (`BN-20260716-DBA96ABF`, non affectée, sans dispositif lié) et `#2` (`ARGOS-DEMO-01`, rattachée à `ARGU0000012`, type « DEMO SYNTHÉTIQUE »). Des positions existent uniquement pour la boîte #2. Cette base permet d'associer deux **scénarios virtuels** à deux boîtes distinctes, mais ne démontre pas la présence de deux dispositifs physiques disponibles.

## Conséquence de conception

Le simulateur ne doit appeler ni l'ingestion IoT réelle, ni l'API de modification des routes opérationnelles, ni le système de notifications/e-mails. Les sessions, routes, mesures et alertes simulées seront conservées dans un espace séparé, marquées synthétiques et présentées comme une couche de démonstration sur la carte. Les règles ARGOS pures peuvent être réutilisées pour évaluer une mesure sans déclencher leurs effets secondaires opérationnels.

## Limites à afficher

La géométrie OSRM/Nominatim est un itinéraire cartographique, pas une route poids lourd certifiée, une observation de circulation ou une consigne de navigation. La couverture, les restrictions de gabarit/tonnage, les frontières, l'état routier et les temps de passage ne sont pas fournis par le routage actuel. L'accélération de l'horloge de scénario et la définition de la métrique « 60 % » doivent rester des paramètres visibles.
