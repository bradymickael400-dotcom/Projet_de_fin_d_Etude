# Simulateur de transport terrestre ARGOS

## Parcours fournis

Le simulateur lance deux scénarios en parallèle, chacun affecté à une boîte ARGOS distincte sélectionnée parmi les boîtes auxquelles le gestionnaire connecté a accès :

1. Douala → N’Djamena : progression de référence, sans incident ajouté au scénario.
2. Kribi → Bertoua : écart latéral, épisode de chocs, ouverture de porte, immobilisation prolongée et épisode de risque de dérapage à faible confiance.

La session dure au plus 60 minutes réelles. L’intervalle d’échantillonnage est réglable de 10 à 600 secondes (60 secondes par défaut); l’accélération de l’horloge va de 1× à 20× (5× par défaut). Ainsi, à 5×, le scénario Kribi–Bertoua peut représenter jusqu’à cinq heures simulées. Les instants et écarts latéraux sont des paramètres de démonstration enregistrés dans la configuration de session.

## Démarrage

1. Appliquer les migrations :

   ```bash
   .venv/bin/python -m app.migrate
   ```

2. Configurer le client Nominatim selon l’installation de l’équipe et les règles d’usage du service :

   ```bash
   export ARGOS_SIMULATOR_USER_AGENT='ARGOS-Transport-Demo/1.0 (contact: equipe@example.org)'
   ```

   Les fenêtres d’événements, le seuil de corridor, la distance latérale de test, l’orientation simulée et les facteurs de chocs sont définis dans `config/terrestrial_transport_scenarios.json`. Le fichier est validé au lancement et sa copie est enregistrée dans la session pour l’audit. `ARGOS_TERRESTRIAL_SIMULATION_CONFIG` peut pointer vers une copie de configuration adaptée; redémarrer le serveur Flask après modification.

   `ARGOS_NOMINATIM_URL` et `ARGOS_OSRM_URL` permettent de choisir des services compatibles exploités par l’organisation. Le service Nominatim public est limité à une requête par seconde et demande une attribution OpenStreetMap; le client impose une pause entre géocodages et indique le fournisseur dans les résultats.

3. Démarrer le worker dans un processus dédié, en complément de Flask :

   ```bash
   .venv/bin/python scripts/argos_terrestrial_scenarios.py
   ```

4. Ouvrir **Carte GPS → Simulateur de transport**, sélectionner deux boîtes distinctes, ajuster l’intervalle et l’accélération, puis démarrer. Le panneau expose l’état du worker et propose pause, reprise et arrêt. La carte trace les routes et positions simulées en tirets violets/ambre; le panneau et les popups portent explicitement la mention de simulation.

Pour vérifier le worker sans session active :

```bash
.venv/bin/python scripts/argos_terrestrial_scenarios.py --once
```

## Calcul de position, vitesse et ETA

Le backend demande au géocodeur les extrémités, puis à OSRM une route `driving` avec géométrie GeoJSON, étapes, distance et durée nominale. Il interpole la position le long de cette géométrie en fonction de la distance et de l’horloge accélérée. La vitesse de déplacement est la vitesse moyenne induite par la distance et la durée OSRM; elle passe à zéro pendant l’arrêt simulé.

L’ETA de référence suit la durée de route OSRM. L’ETA courant tient compte de la distance restante et du temps d’immobilisation restant. L’écart entre les deux est affiché en minutes. Cela rend visible l’effet de l’arrêt dans le scénario; il ne s’agit pas d’une prévision apprise ni d’une estimation à partir du trafic réel.

Chaque échantillon construit un lot UUID conforme au contrat de validation IoT réel (position, cap, vitesse, mesures, modes, qualité et séquence), puis le valide localement avec `validate_telemetry_payload`. Ce lot est conservé dans la table de simulation pour audit; il n’est pas envoyé à `/api/iot/telemetry` et son identifiant d’appareil `ARGOS-SIM-*` ne possède pas de clé d’authentification.

Les règles ARGOS déterministes d’alerte de seuil, d’écart d’itinéraire et de risque sont évaluées sans leurs effets secondaires. Les épisodes restent confinés aux tables de simulation et portent une provenance `SYNTHETIC`. Les modèles/agents qui lisent les mesures opérationnelles ne sont pas appelés avec ces échantillons; le résultat est une évaluation des règles et de leur regroupement en épisodes, pas un essai d’un modèle ML déployé.

## Cloisonnement et accès

- Les sessions, scénarios, échantillons et épisodes résident dans `argos_transport_sim_sessions`, `argos_transport_sim_scenarios`, `argos_transport_sim_samples` et `argos_transport_sim_episodes`.
- Le simulateur n’appelle ni l’ingestion `/api/iot/telemetry`, ni la télémétrie directe des boîtes, ni l’écriture des routes planifiées réelles, ni la création des notifications opérationnelles et e-mails.
- L’API requiert l’authentification ARGOS. Seuls `superadmin` et `owner` peuvent créer ou commander une session. La lecture des sessions est restreinte aux boîtes visibles par le profil. Deux boîtes distinctes et autorisées sont obligatoires; une boîte engagée dans une autre session active est refusée.
- Un verrou advisory PostgreSQL empêche le démarrage de plusieurs workers. Une interruption du worker ne fait pas avancer l’horloge de scénario; les sessions actives reprennent au prochain lancement.
- Les coordonnées simulées et les marqueurs de télémétrie réelle utilisent des couches différentes. L’historique réel et ses traces restent servis par leurs API habituelles.

## Limites de la route

La géométrie OSRM/Nominatim est un itinéraire cartographique de référence. Le profil `driving` ne confirme pas les restrictions de poids ou de hauteur, l’ouverture de frontière, l’état du revêtement, les contrôles routiers ni l’admissibilité d’un véhicule lourd. Aucune circulation temps réel, météo, fermeture de route ou durée réelle de passage frontière n’entre dans l’ETA. La route affichée ne doit donc pas être présentée comme navigation poids lourd certifiée.

L’événement de dérapage est seulement un événement synthétique de scénario : l’application indique une confiance faible et les entrées manquantes (accélération latérale, chaussée et pluie/adhérence). L’orientation de porte et l’incident routier portent eux aussi la provenance simulée; aucun signal ne décrit une boîte physique.

Les services publics peuvent limiter le débit, modifier leurs données ou être indisponibles. Sans réponse de géocodage ou de routage valide, la création échoue; aucune ligne droite n’est substituée à une route routière.

## Vérification

Les tests unitaires couvrent l’interpolation GPS, le décalage simulé, les scénarios, les événements, l’immobilisation et son effet sur l’ETA, les réponses OSRM invalides ainsi que l’autorisation de lecture/création. Exécution :

```bash
.venv/bin/python -m pytest -q tests/test_terrestrial_simulation_service.py
node --check app/static/js/data-pages.js
```
