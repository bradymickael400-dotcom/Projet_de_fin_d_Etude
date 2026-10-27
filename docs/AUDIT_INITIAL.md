# Audit initial ARGOS Intelligence

Date de l'inspection : 27 octobre 2026 (Africa/Douala). Périmètre : dépôt racine Flask, configuration, API, IoT, services de positionnement/maritime, interface statique, scripts et migrations. Aucun secret n'est reproduit dans ce rapport.

## Résumé exécutif

Le dépôt contient une application ARGOS opérationnelle au sens logiciel : backend Flask, API métier, authentification par jeton signé, ingestion IoT avec validation et persistance PostgreSQL, cache Redis facultatif/obligatoire selon l'environnement, règles d'alertes, commandes appareil, positionnement hybride IoT/AIS, documents et interfaces web. Le code ne prouve pas que les services externes ou le matériel fonctionnent dans l'environnement inspecté.

Deux routes d'appel LLM existent (Gemini et DeepSeek), mais aucun registre d'agents, orchestrateur, contrat d'échange inter-agents, modèle prédictif, pipeline RAG ou base documentaire interrogée n'a été trouvé. Les alertes observées dans le pipeline IoT reposent sur validation, seuils et règles métier, pas sur un modèle IA.

Le dépôt est dans un état Git fortement modifié (fichiers staged, unstaged, ajoutés et supprimés). Ces changements préexistants ont été conservés; les documents de ce lot sont ajoutés dans `docs/` à la racine pour ne pas modifier le rapport parallèle `ARGOS_RAPPORT_FINAL_MODIFIE/`.

## Architecture réellement repérée

```text
ESP32 / simulateur / pont navigateur
  -> routes Flask (API IoT et métier)
  -> validation et normalisation Python
  -> Redis (flux court si configuré) + PostgreSQL (mesures, positions, événements)
  -> seuils, notifications, journal d'audit et commandes
  -> API de tableau de bord / pages HTML, CSS et JavaScript

API de positionnement -> dernière position IoT / AIS enregistrée / dernière position connue
API IA -> appel Gemini (route ReportAI) ou proxy DeepSeek distinct
```

Le schéma SQL principal est créé par un ensemble de migrations SQL (`app/migrate.py`, dossier `migrations/`) et certaines tables IoT sont aussi créées à la demande par `app/modules/iot/repository.py`. Les documents de conception dans le dossier du rapport et les diagrammes ne constituent pas une preuve d'exécution.

## Inventaire de capacités

| Capacité | Classement | Preuve dans le dépôt / exécution | Conséquence |
|---|---|---|---|
| Application Flask et routes métier | Présente, non vérifiée en exécution | `app.py`, `app/__init__.py`, `app/routes/*`; dépendances Python indisponibles localement | Conserver comme socle; vérifier démarrage en environnement doté des dépendances. |
| Authentification API et contrôle de rôles | Présente, partiellement vérifiée | `app/security.py` applique une politique par défaut aux `/api/`, jetons signés et registre d'identité | Indispensable; auditer chaque route et permissions lors de la phase suivante. |
| Ingestion/validation IoT | Présente, non vérifiée bout en bout | `app/modules/iot/{controller,iot_service,validator,normalizer,repository}.py` | Conserver; aucun dossier `tests/` racine n'était présent dans l'arbre de travail inspecté. |
| Détection par seuils et notifications | Fonctionnelle dans le code, résultat runtime non vérifié | `iot_event_service.py`, appelé par `iot_service.py` | Conserver comme règles explicables; ne pas la qualifier de modèle IA. |
| Cache temps réel | Présent, partiel selon config | `telemetry_cache.py`, Redis dans Compose; repli PostgreSQL prévu | Conserver; prouver mode Redis et mode dégradé séparément. |
| Positionnement IoT/AIS | Partiellement fonctionnel | `positioning_service.py`, adaptateurs `maritime_service.py`; certains endpoints Vizion d'historique navire retournent `None` | Conserver; vérifier fournisseurs, fraîcheur et indisponibilité. |
| Données GPS de démonstration | Simulées | `scripts/simulate_argos_box.py`, `simulateur_iot.py` fabriquent des positions de scénario | À identifier visiblement comme simulation; non représentatives de terrain. |
| LLM Gemini | Présent mais non vérifié | `app/routes/dashboard.py::ai_chat`, dépendance Google dans `requirements.txt`, clé `API_KEY` | Connexion externe non démontrée; route reçoit aussi `contextData` du client. |
| Proxy LLM DeepSeek | Présent, non vérifié et secondaire | `app/routes/containers.py::ai_chat_deepseek`; secret `DEEPSEEK_API_KEY`; commentaire indique non appelé par défaut | Redondance de fournisseur/contrat à clarifier avant toute consolidation. |
| Agents métier et orchestration | Absents | Aucun module agent, registre ou coordinateur découvert dans `app/` | À concevoir seulement après validation de l'audit. |
| RAG / corpus documentaire / index vectoriel | Absents | Aucun ingestion de corpus, embedding ou retrieval découvert | Aucune réponse réglementaire sourcée ne peut être revendiquée. |
| Détection ML/anomalies prédictive | Absente | Aucune définition/artefact de modèle découvert; règles de seuil seules | Ne pas présenter les règles comme apprentissage automatique. |
| Carte interactive | Présente côté interface / non vérifiée | `app/static/js/*`, positions via API; fournisseur de carte exact à confirmer dans le parcours | Vérifier rendu et provenance en phase dédiée, sans inventer de GPS. |
| Rapports PDF/documents | Présents | `app/services/report_service.py`, `storage_service.py`, routes workflow | Conserver; vérifier permissions et stockage. |
| Tests automatisés racine | Absents de l'arbre de travail courant | `find tests` ne trouve aucun dossier; `git status` signale des fichiers `tests/*` indexés comme ajouts puis supprimés dans l'arbre courant (état préexistant) | Impossible de les exécuter ou d'en conclure le résultat; restaurer/localiser avant validation complète. |

Les états « fonctionnelle » et « présente » qualifient ici les chemins de code inspectés, pas une validation d'environnement ou de production.

## Fonctions à conserver / modifier / supprimer

| Décision | Éléments | Justification et preuve |
|---|---|---|
| Conserver | Authentification, rôles, API, base relationnelle, migrations, validation IoT, provenance des positions, journaux, seuils, carte, stockage de documents | Socle métier et sécurité déjà présent; aucun élément ne peut être déclaré inutile à partir de l'audit. |
| Modifier / consolider ultérieurement | Routes LLM et contrat d'entrée, traitement des données de contexte client, distinction données réelles/simulées, dépendances du schéma dynamique, observabilité des appels externes | Gemini reçoit `contextData` transmis par le client; les deux fournisseurs ont des contrats et comportements différents; preuves d'intégration absentes. |
| Supprimer | Rien à ce stade | Pas de preuve suffisante de redondance inutile ou d'incompatibilité. Toute suppression doit attendre une analyse d'impact et un remplacement. |

## Preuves d'inspection et vérifications initiales

- `app/__init__.py` enregistre les blueprints métier, active CORS sur `/api/*` et attache le contrôle d'authentification.
- `app/modules/iot/validator.py` vérifie UUID, type, horodatage ISO-8601, séquence, bornes GPS et champs capteurs.
- `app/modules/iot/iot_service.py` suit validation → authentification appareil → association → normalisation → cache → persistance → audit/alertes.
- `app/services/positioning_service.py` retourne des métadonnées de source/fraîcheur et peut distinguer position IoT, AIS, dernière position connue ou indisponible.
- `app/routes/dashboard.py` implémente un appel Gemini; `app/routes/containers.py` implémente un appel DeepSeek séparé.
- `docker-compose.yml` déclare PostgreSQL/TimescaleDB, Redis, application, worker et tunnel Cloudflare.
- L'environnement hôte n'a ni `python` (seulement `python3`), ni Flask, pytest, Redis client Python, psycopg ou paho-mqtt installés. Les commandes `python` échouent; l'import ou les tests applicatifs ne sont donc pas exécutables sans installer des dépendances.
- Docker est présent, mais aucune stack n'a été démarrée afin d'éviter toute mutation de base ou lancement réseau non nécessaire à l'audit.
- Aucun secret trouvé n'est divulgué. Des noms de variables sensibles sont documentés dans `.env.example`; vérifier le contenu réel des fichiers d'environnement hors audit avant partage public.

## Limites de cet audit

Pas de preuve de connexion PostgreSQL/Redis, matériel ESP32, fournisseurs maritimes, Gemini ou DeepSeek. Pas de capture runtime. L'arbre courant contient de nombreux changements Git préexistants, ce qui limite les conclusions sur l'état historique des tests et sur les modifications en cours. Les livrables restent un audit statique étayé par le code.
