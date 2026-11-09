# Simulation télémétrique d’Afrique centrale

Le fichier `datasets/argos_central_africa_60min.json` transmet une heure de mesures de simulation à une boîte ARGOS existante, liée à un conteneur sec standard. Le script utilise l’API authentifiée, reprend la séquence de télémétrie et envoie une mesure par minute. Il ne crée ni entreprise, ni conteneur, ni boîte.

## Boîte standard active disponible dans l’environnement local

Dans l’instance Docker `http://localhost:5002`, la boîte **1** est active, liée au conteneur sec **MSCU200900NNNNNN**. L’appareil associé est encore `PENDING_ENROLLMENT`; le script envoie donc les données de simulation par le pont direct authentifié ARGOS, pas depuis un ESP32 connecté. Le conteneur `ARGU0000012` est l’ancien conteneur synthétique de présentation; le script refuse maintenant de l’utiliser pour ce jeu standard.

## Commande

    python3 scripts/stream_transport_scenario.py --box-id 1

Le script demande un compte autorisé à gérer cette boîte et son mot de passe. Une valeur de conteneur peut aussi remplacer l’ID de boîte, par exemple `--box-id MSCU200900NNNNNN`; le script résout la relation active et refuse les conteneurs synthétiques.

Le scénario dure 60 minutes : 61 mesures, espacées de 60 secondes. Il configure l’itinéraire et les seuils ARGOS du scénario avant l’émission. Ces réglages restent sur la boîte à la fin afin que le corridor et les alertes soient consultables. `--no-route-update` et `--no-threshold-update` conservent respectivement la configuration existante.

## Incidents inclus

- proximité indicative du Port de Douala au début;
- choc modéré puis choc sévère;
- écart au corridor planifié;
- dépassements de vitesse;
- ouverture avec alarme de sécurité;
- excursion de température et d’humidité;
- détection de flamme;
- batterie faible;
- immobilisation prolongée vers Édéa.

L’immobilisation prolongée est maintenant évaluée même hors d’une zone géographique nommée. Les coordonnées restent dans le corridor routier Douala–Édéa–Pouma–Yaoundé au Cameroun. Les anomalies sont synthétiques et servent à éprouver les agents; ce jeu n’est pas une mesure physique ni un itinéraire de navigation.

Dans l’application, ouvrir **Carte GPS** avec un compte autorisé sur la boîte et garder **Actualisation auto (10 s)** activée pour suivre les positions et alertes. La visibilité par boîte et par entreprise reste appliquée.
