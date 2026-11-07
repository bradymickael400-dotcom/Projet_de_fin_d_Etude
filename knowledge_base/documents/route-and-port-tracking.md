# Suivi ARGOS des routes et des zones portuaires

## APIs de suivi par boîte

- `GET /api/black-boxes/{id}/route-tracking?limit=300` retourne l'itinéraire prévu, les positions autorisées de la boîte, un score géométrique explicable pour chaque point, les séquences au-dessus du seuil, le score/distance maximum et des segments cartographiques. Le paramètre `limit` est limité à 2 000 points.
- `GET /api/black-boxes/{id}/port-tracking?limit=500&include_points=false` retourne les points de proximité portuaire et les transitions entrée/sortie de zones configurées. Avec `include_points=true`, la réponse inclut la trace et, par point, les zones et repères portuaires proches.
- Les deux API vérifient le rôle et l'accès à la boîte. Un utilisateur ne peut consulter que les trajets des boîtes déjà présentes dans son périmètre ARGOS; une boîte sans conteneur n'est accessible par ces APIs qu'au superadmin.

## Interprétation de l'itinéraire

Le corridor est un chemin attendu saisi par un gestionnaire. ARGOS mesure la distance entre chaque point GPS et les segments du corridor, corrige l'incertitude horizontale déclarée et calcule un score opérationnel borné à 100. Le seuil est propre à la route. Le score n'est ni une probabilité d'incident ni une prévision ML. Une alerte indique le point/horodatage, la distance et le seuil; l'interface peut colorer le tronçon en rouge.

## Interprétation portuaire

- `port_proximity_entry` et `port_proximity_exit` indiquent le franchissement du rayon autour d'un point de référence portuaire. La réponse fournit le rayon, la distance, la précision et le statut de vérification de la coordonnée.
- `geofence_entry` et `geofence_exit` indiquent le franchissement d'un polygone configuré dans ARGOS. Ils ne prouvent une entrée portuaire officielle que si le polygone a été fourni/validé par l'autorité compétente.
- `*_at_window_start` signifie que la trace commence déjà dans la zone ou le rayon; il ne faut pas l'interpréter comme une transition observée.
- Des positions trop espacées peuvent manquer une entrée/sortie entre deux mesures. Présenter l'événement comme une détection issue des points reçus, avec ses heures et limites de couverture.

## Compétences des agents

`gps_route` consomme le suivi enrichi, présente l'état courant et la trace récente, et explique les écarts par rapport au corridor. `port_intelligence` contextualise les ports et statistiques sourcés, énumère les transitions détectées sur la boîte explicitement autorisée et distingue proximité indicative et zone configurée. Les deux agents signalent les données manquantes, la fraîcheur et les incertitudes géographiques.
