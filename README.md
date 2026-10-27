# ARGOS

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

## Vérifications

```bash
.venv/bin/python -m pytest -q tests
node --test tests/js/phase3-ui.test.cjs
```

Les résultats réellement observés, les échecs, la procédure d’essai navigateur et les limites sont dans [docs/PHASE4_POINT_CONTROLE.md](docs/PHASE4_POINT_CONTROLE.md) et [docs/TESTS_ET_PREUVES.md](docs/TESTS_ET_PREUVES.md).
