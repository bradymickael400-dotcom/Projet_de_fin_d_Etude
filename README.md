
# TEAM ARGOS SUP'PTIC CAMEROUN — Graduation Project (End-of-Studies Project)

ARGOS is a Flask application for logistics, container supervision, IoT, and GPS positioning. The interface uses server APIs; the assistant routes through the backend multi-agent orchestrator.

## Local Setup

Prerequisites: Python 3.12, PostgreSQL (`brady` schema), Redis, and Node.js for browser testing. From the root directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt pytest
cp .env.example .env   # only if .env does not already exist

```

In `.env`, configure the PostgreSQL parameters, `SECRET_KEY`, `INITIAL_ADMIN_PASSWORD`, and, to enable the assistant, `API_KEY` (Gemini API key). Do not publish this file.

After starting PostgreSQL and Redis, initialize the schema and the administrator account, then launch Flask:

```bash
python -m app.bootstrap
flask --app app.py run --host 127.0.0.1 --port 5002

```

The repository's Docker workflow is `docker compose up -d --build db redis web worker`; `./start-argos.sh` also adds a public Cloudflare tunnel. Migrations are executed by `app.bootstrap` when the web container starts. The Compose configuration references the existing lowercase build file `dockerfile`.

## Terrestrial Transport Simulator

The manager-only simulator displays two demonstration scenarios on the ARGOS map: Douala → N’Djamena and Kribi → Bertoua. It uses two distinct authorized black boxes, a session of at most 60 minutes, and an adjustable interval (60 seconds by default). Simulated data remains isolated from IoT measurements and operational notifications.

Configure a User-Agent identifying the application and a team contact, then apply migrations and run the worker in a separate terminal from the Flask server:

```bash
export ARGOS_SIMULATOR_USER_AGENT='ARGOS-Transport-Demo/1.0 (contact: equipe@example.org)'
# Optional: path to a tailored event configuration
# export ARGOS_TERRESTRIAL_SIMULATION_CONFIG=/path/to/terrestrial_transport_scenarios.json
.venv/bin/python -m app.migrate
.venv/bin/python scripts/argos_terrestrial_scenarios.py

```

Then open **GPS Map → Transport Simulator**, select two distinct black boxes, and start. Details, routing limitations, and evaluation are provided in [docs/SIMULATEUR_TRANSPORT_TERRESTRE.md](https://www.google.com/search?q=docs/SIMULATEUR_TRANSPORT_TERRESTRE.md); the preliminary audit is in [docs/AUDIT_SIMULATEUR_TERRESTRE_ARGOS.md](https://www.google.com/search?q=docs/AUDIT_SIMULATEUR_TERRESTRE_ARGOS.md). OSRM routes do not validate heavy vehicle restrictions and do not provide real-time traffic data.

## AI for Good Scenario: Freight and Public Policy Roles

The `silent_container_v1` scenario replays six fictitious steps with four siloed roles and a location transfer blocked pending human review. The deterministic replay requires neither a Gemini key nor a database:

```bash
.venv/bin/python scripts/run_policy_scenario.py --output /tmp/argos_policy_scenario.json
.venv/bin/python scripts/evaluate_policy_kb.py
.venv/bin/python scripts/export_itu_readiness_kb.py --output-dir /tmp/argos_itu_export

```

The authenticated API endpoint is `POST /api/ai/policy-scenarios/silent_container_v1/run`; the body `{ "use_llm": true }` activates separate Gemini calls per role, on synthetic facts only. Without this option, the deterministic mode makes no external calls. To store and review API traces, apply the migration `20261102_policy_scenario_runs.sql`; the response indicates `audit_persisted` if the write succeeded. Document partitions, ITU AI Readiness code, and their limitations are described in [the integration note](https://www.google.com/search?q=docs/ITU_AI_READINESS_REFERENCE_INTEGRATION.md); the gap analysis is in [the submission audit](https://www.google.com/search?q=docs/AUDIT_AI_FOR_GOOD_ARGOS_FR.md).

French and English versions of the submission form, complete with template structure and tables, are located in `docs/submissions/ARGOS_Template_Structure_FR.pdf` and `docs/submissions/ARGOS_Template_Structure_EN.pdf` (with neighboring editable `.md` and `.docx` sources). These documents remain prototype reports: team fields must be filled in, and open external validations are explicitly noted.

One-page presentation sheets are available in [French](https://www.google.com/search?q=docs/submissions/ARGOS_One_Page_FR.pdf) and [English](https://www.google.com/search?q=docs/submissions/ARGOS_One_Page_EN.pdf), alongside their Markdown sources and Word files in the same folder.

## Verifications

```bash
.venv/bin/python -m pytest -q tests
node --test tests/js/*.test.cjs

```

Actual observed results, failures, browser testing procedures, and limitations are detailed in [docs/PHASE4_POINT_CONTROLE.md](https://www.google.com/search?q=docs/PHASE4_POINT_CONTROLE.md) and [docs/TESTS_ET_PREUVES.md](https://www.google.com/search?q=docs/TESTS_ET_PREUVES.md).
