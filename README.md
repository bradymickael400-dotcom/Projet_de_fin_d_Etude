# ARGOS — Projet de fin d’étude

ARGOS est une application Flask de supervision logistique, conteneurs, IoT et positions GPS. L’interface utilise les API du serveur; l’assistant passe par l’orchestrateur multi-agents côté backend.

## Démarrage local

Prérequis : Python 3.12, PostgreSQL (schéma `brady`), Redis et Node.js pour les tests du navigateur. Depuis la racine :

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt pytest
cp .env.example .env   # seulement si .env n’existe pas déjà
```

Renseigner dans `.env` les paramètres PostgreSQL, `SECRET_KEY`, `INITIAL_ADMIN_PASSWORD` et, pour activer l’assistant, `API_KEY` (clé Gemini). Ne pas publier ce fichier.

Après le démarrage de PostgreSQL et Redis, initialiser le schéma et le compte administrateur, puis lancer Flask :

```bash
python -m app.bootstrap
flask --app app.py run --host 127.0.0.1 --port 5002
```

Le parcours Docker du dépôt est `docker compose up -d --build db redis web worker`; `./start-argos.sh` ajoute aussi un tunnel public Cloudflare. Les migrations sont exécutées par `app.bootstrap` au démarrage du conteneur web. La configuration Compose désigne le fichier de construction existant `dockerfile` (minuscule).

## Simulateur de transport terrestre

Le simulateur réservé aux gestionnaires affiche deux scénarios de démonstration sur la carte ARGOS : Douala → N’Djamena et Kribi → Bertoua. Il utilise deux boîtes distinctes autorisées, une session d’au plus 60 minutes et un intervalle réglable (60 secondes par défaut). Les données simulées restent isolées des mesures IoT et des notifications opérationnelles.

Configurer un User-Agent qui identifie l’application et un contact de l’équipe, puis appliquer les migrations et lancer le worker dans un terminal séparé du serveur Flask :

```bash
export ARGOS_SIMULATOR_USER_AGENT='ARGOS-Transport-Demo/1.0 (contact: equipe@example.org)'
# Optionnel : chemin vers une configuration d'événements adaptée
# export ARGOS_TERRESTRIAL_SIMULATION_CONFIG=/chemin/vers/terrestrial_transport_scenarios.json
.venv/bin/python -m app.migrate
.venv/bin/python scripts/argos_terrestrial_scenarios.py
```

Ouvrir ensuite **Carte GPS → Simulateur de transport**, sélectionner deux boîtes noires distinctes et démarrer. Détails, limites de routage et évaluation figurent dans [docs/SIMULATEUR_TRANSPORT_TERRESTRE.md](docs/SIMULATEUR_TRANSPORT_TERRESTRE.md); l’audit préalable est dans [docs/AUDIT_SIMULATEUR_TERRESTRE_ARGOS.md](docs/AUDIT_SIMULATEUR_TERRESTRE_ARGOS.md). Les routes OSRM ne valident pas les restrictions poids lourd et ne fournissent pas de trafic temps réel.

## Scénario AI for Good : fret et rôles de politique publique

Le scénario `silent_container_v1` rejoue six étapes fictives avec quatre rôles cloisonnés et un transfert de localisation bloqué en attente de revue humaine. Le rejeu déterministe ne nécessite ni clé Gemini ni base de données :

```bash
.venv/bin/python scripts/run_policy_scenario.py --output /tmp/argos_policy_scenario.json
.venv/bin/python scripts/evaluate_policy_kb.py
.venv/bin/python scripts/export_itu_readiness_kb.py --output-dir /tmp/argos_itu_export
```

L’API authentifiée est `POST /api/ai/policy-scenarios/silent_container_v1/run`; le corps `{ "use_llm": true }` active des appels Gemini séparés par rôle, sur des faits synthétiques uniquement. Sans cette option, le mode déterministe ne fait aucun appel externe. Pour conserver et relire les traces API, appliquer la migration `20261102_policy_scenario_runs.sql`; la réponse indique `audit_persisted` si l’écriture a réussi. Les partitions documentaires, le code ITU AI Readiness et leurs limites sont décrits dans [la note d’intégration](docs/ITU_AI_READINESS_REFERENCE_INTEGRATION.md); l’analyse d’écarts est dans [l’audit de soumission](docs/AUDIT_AI_FOR_GOOD_ARGOS_FR.md).

Les versions françaises et anglaises du formulaire de soumission, avec la structure et le tableau du modèle, sont dans `docs/submissions/ARGOS_Template_Structure_FR.pdf` et `docs/submissions/ARGOS_Template_Structure_EN.pdf` (sources éditables `.md` et `.docx` voisines). Les documents restent des rapports de prototype : les champs équipe sont à renseigner et les validations externes ouvertes sont explicitées.

Les fiches de présentation d’une page sont disponibles en [français](docs/submissions/ARGOS_One_Page_FR.pdf) et [anglais](docs/submissions/ARGOS_One_Page_EN.pdf), avec leurs sources Markdown et fichiers Word dans le même dossier.

## Vérifications

```bash
.venv/bin/python -m pytest -q tests
node --test tests/js/*.test.cjs
```

Les résultats réellement observés, les échecs, la procédure d’essai navigateur et les limites sont dans [docs/PHASE4_POINT_CONTROLE.md](docs/PHASE4_POINT_CONTROLE.md) et [docs/TESTS_ET_PREUVES.md](docs/TESTS_ET_PREUVES.md).
