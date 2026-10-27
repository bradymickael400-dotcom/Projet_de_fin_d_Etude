# Architecture existante ARGOS

Inspection du 27 octobre 2026. Ce document décrit le code observé dans le dépôt racine; il ne certifie pas l'exécution des composants externes.

## Pile et démarrage

- Backend : Python 3, Flask, Flask-SQLAlchemy, Flask-CORS et Flask-Limiter (`requirements.txt`). `app.py` crée l'application avec `create_app()`.
- Interface : pages Jinja (`app/templates/`), CSS, JavaScript natif (`app/static/`); aucune compilation frontend identifiée.
- Persistance : PostgreSQL (`psycopg`, `psycopg2`), schéma configurable `brady`; migrations SQL via `app/migrate.py`, puis initialisation via `app/bootstrap.py`.
- Temps réel : Redis via `app/modules/iot/telemetry_cache.py`; configuration Compose rend le Redis IoT obligatoire en déploiement alors que le défaut applicatif permet un mode non obligatoire.
- Déploiement : Docker Compose construit l'image Python, démarre DB/Redis/web/worker et Cloudflared. `dockerfile` lance bootstrap puis Gunicorn; `start-argos.sh` démarre la stack et crée/actualise un tunnel public.
- Firmware : Arduino/ESP32 sous `firmware/argos_esp32/`; simulateurs sous `scripts/` et à la racine. Le matériel n'a pas été connecté ni testé.

## Flux de données

1. Les routes IoT (`app/modules/iot/controller.py`) reçoivent enrôlement, télémétrie, commandes, accusés et audio. Un second flux de pont navigateur est présent.
2. `validator.py` contrôle le payload, les mesures et le timestamp; `normalizer.py` prépare qualité et événement.
3. `iot_service.py` associe le device à une boîte/conteneur, vérifie les séquences, publie dans Redis, persiste lecture/capteurs/position, crée l'audit et déclenche les alertes configurées.
4. `iot_event_service.py` produit alertes de seuil et notifications. C'est un moteur de règles, pas un modèle prédictif.
5. Les routes de télémétrie/tableau de bord et les scripts frontend exposent statistiques et détails.
6. `positioning_service.py` choisit notamment position IoT récente, AIS stockée ou dernière position connue; sinon retourne une position indisponible.

## API, identité et sécurité observées

Les blueprints enregistrés dans `app/__init__.py` couvrent authentification, conteneurs, télémétrie, tableau de bord, blockchain, utilisateurs, publications, maritime, boîtes noires, IoT et workflows. `app/security.py` applique aux `/api/` un refus par défaut sans jeton signé, avec exceptions explicites pour les endpoints publics. Les rôles et contrôles d'accès supplémentaires sont dispersés dans les routes/services. CORS autorise actuellement toutes les origines sur les API.

La route Gemini est `/api/ai/chat` et est protégée par la politique globale API hors exceptions. La route DeepSeek `/api/ai/deepseek` est également implémentée. Leur disponibilité dépend de clés serveur et d'accès réseau; aucun appel n'a été effectué pendant l'audit.

## Stockage

Le schéma est créé à la fois par migrations versionnées (`migrations/*.sql`) et par fonctions d'initialisation paresseuse dans certains modules. Les lectures IoT et positions reposent sur PostgreSQL; Redis est utilisé comme flux/cache récent avec repli applicatif annoncé vers PostgreSQL. Les documents privés peuvent être stockés dans un volume Docker.

## Composants absents ou non établis

- Aucun registre ni contrat de messages inter-agents.
- Aucun coordinateur ni mécanisme d'appel d'un agent à un autre.
- Aucun modèle ML, artefact d'entraînement ou métrique évaluée.
- Aucun pipeline de base documentaire, RAG, embeddings ou citations vérifiables.
- Pas de preuve runtime des services cités ni du démarrage propre sur l'hôte inspecté.

## Architecture cible proposée (proposition, non implémentée)

```text
Sources IoT/GPS et fournisseurs externes
  -> ingestion existante + validation/provenance
  -> stockage opérationnel existant
  -> services métier existants (règles, position, incidents)
  -> interfaces de capacités explicites (à concevoir)
  -> coordinateur à contrat commun (à concevoir)
  -> LLM avec outils autorisés et résultats sourcés (à concevoir)
  -> API sécurisée existante / interface existante
```

Garder la validation, le contrôle d'accès, les seuils et le stockage comme frontières déterministes. Le LLM ne doit pas remplacer les mesures, exécuter de commande physique ni inventer une position. Tout nouveau composant doit réutiliser les services existants et établir sa provenance avant d'ajouter une dépendance lourde. Cette cible nécessite validation avant implémentation.
