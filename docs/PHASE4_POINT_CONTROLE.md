# Phase 4 — Validation et point de contrôle

Date : 27 octobre 2026. Périmètre exécuté : tests ARGOS, contrôles de sécurité ciblés, appels réels des API disponibles, test navigateur et tentative LLM réelle. Le rendu dashboard a aussi été retravaillé après le retour sur la visibilité du design.

## Résultat résumé

Le contrat multi-agents et les tests frontend passent. Les API de tableau de bord et de positions ont répondu 200 pendant le parcours navigateur. Un parcours Flask via le registre réel et les agents IoT/GPS a répondu 200 avec le fournisseur de test et a persisté sa trace. L’appel au fournisseur Gemini réel a échoué HTTP 503; aucune réponse LLM réelle, aucun appel d’agent déclenché par un vrai Gemini et aucun parcours réglementaire complet ne sont revendiqués comme réussis.

## Interface et preuves navigateur

La vue d’ensemble a maintenant une hiérarchie de supervision, des cartes KPI alimentées par API dans le DOM, une grille carte/alertes, des états vides, des contrôles nommés et des points de rupture mobile. Le compteur de notifications fictif fixé à `4` a été supprimé. Les versions d’assets ont été incrémentées afin d’éviter que le navigateur conserve les fichiers de la phase 3. Compose référence maintenant le fichier existant `dockerfile` en minuscules.

Playwright/Chromium a réellement ouvert l’application Flask locale. Le serveur de preuve injectait une identité superadmin uniquement pour ce processus; les handlers d’API et la base locale n’étaient pas simulés. Les réponses observées incluent `/api/dashboard/superadmin` 200, `/api/blockchain/stats` 200, `/api/containers/all` 200 et `/api/containers/positions` 200. La liste de positions était vide. Aucune erreur JavaScript n’a été observée; à 390 px, largeur de document = largeur de fenêtre (390 px) et panneau IA = 366 px.

Les alertes du tableau de bord proviennent de données présentes dans la base locale. Leur texte a été flouté dans les captures afin de ne pas publier leur contenu métier. La conversation affichée est l’accueil de l’assistant, pas une réponse Gemini.

- [Tableau de bord](phase4/captures/tableau-de-bord.png)
- [Carte GPS (aucune position disponible)](phase4/captures/carte-gps.png)
- [Assistant global (état d’accueil)](phase4/captures/assistant-global.png)
- [Assistant sur mobile](phase4/captures/assistant-mobile.png)
- [Tableau de bord revu, KPI visibles](phase4/captures/tableau-de-bord-revue.png)
- [Carte GPS revue et état sans coordonnées](phase4/captures/carte-gps-revue.png)
- [Assistant avec choix de plusieurs conteneurs et marque 3D](phase4/captures/assistant-global-revue.png)
- [Assistant revu sur mobile](phase4/captures/assistant-mobile-revue.png)

## Résultats exécutés

| Vérification | Exécution observée | Résultat |
|---|---|---|
| Python ARGOS | `PYTHONPATH=. .venv/bin/pytest -q tests` | 16 réussis : handlers des quatre agents, échanges IoT/GPS→risque, LLM simulé multi-outils, périmètre multi-boîtes et refus boîte non autorisée, classifieur hors secteur simulé, RAG et contrôles d’accès. |
| Frontend JS | `node --check` sur les cinq modules; `node --test tests/js/phase3-ui.test.cjs` | Syntaxe OK; 6 réussis, dont le dialogue de sélection multiple. |
| Parcours navigateur | Chromium headless sur Flask local, bureau puis 390×844 | API de page réelle observée en 200; sélecteur chat renvoyé par une interception de test, puis les cases 17/18 vérifiées dans la requête du navigateur. Aucune erreur JS ni débordement mobile. Identité de capture injectée; authentification de production non couverte. |
| API + agents + audit | `POST /api/ai/chat` avec fournisseur d’outils de test et handlers IoT/GPS non remplacés | HTTP 200; `iot_monitor=empty`, `gps_route=empty`; trace créée et relue depuis `brady.ai_agent_runs`. Ce n’est pas un test LLM externe réel. |
| LLM externe réel | `POST /api/ai/chat` via `GeminiToolProvider` configuré | Échec HTTP 502 côté ARGOS après HTTP 503 Gemini. Trace rendue; la table d’audit manquait lors du premier appel. Aucune réponse ni tool call réel. |
| Authentification sécurité | GET API avec seuls en-têtes `X-Role` et `X-User-Id` forgés | 401 `AUTH_REQUIRED`. |
| Migration | Exécution de `migrations/20261027_ai_agent_runs.sql` sur DB locale | Table `brady.ai_agent_runs` confirmée présente. |
| Compose | `docker compose config --quiet` | Réussi. |
| Dépendances navigateur temporaires | `npm audit --omit=dev --audit-level=high --package-lock-only --prefix /tmp/argos-phase3-browser` après correction | 0 vulnérabilité dans l’outil temporaire. Le dépôt n’a pas de manifeste npm racine. |
| Arthena | `/tmp/argos-phase2-venv/bin/python -m pytest -q arthena_flask/tests` | Non exécuté : collecte échouée, `ModuleNotFoundError: flask_migrate`. |
| Collection globale | `/tmp/argos-phase2-venv/bin/python -m pytest -q` | Échec de collecte : dépendance manquante et collision du package `app`. |
| Scanner Python | `pip-audit`, Bandit | Non exécutés; exécutables absents. |

## Scénarios d’acceptation

| Scénario | Observé |
|---|---|
| A — données consultables | API de synthèse 200; routes de positions et conteneurs 200. Ces deux dernières renvoient zéro ligne. Ingestion réelle non couverte. |
| B — perte de communication | La logique de fraîcheur/position ancienne est couverte par un test unitaire simulé; perte matériel réelle non exécutée. |
| C — écart de trajet | Non exécuté : aucune position ni route réelle disponible. |
| D — anomalie IoT | Le test de règles démontre la consommation de signaux simulés; aucun modèle ML ni incident capteur réel validé. |
| E — multi-agents | Test provider simulé : plusieurs outils appelés au même tour et leurs réponses renvoyées au LLM simulé. Appel Gemini réel bloqué par HTTP 503. |
| F — partage transversal | Le test montre `risk_assessor` consommant les résultats `iot_monitor` et `gps_route`; l’API locale avec capacités réelles a renvoyé leurs états `empty`. |
| G — question réglementaire | RAG local et références de fichier/lignes testés avec document temporaire; corpus réglementaire métier et réponse Gemini réelle non validés. |
| H — donnée manquante | API et interface signalent l’absence de position; pas de marqueur inventé. |
| I — refus hors domaine | Non exécuté sur un LLM fonctionnel. |
| J — injection | Le test vérifie que `contextData`/`systemPrompt` du navigateur ne remplacent pas le prompt serveur; le corpus symlink externe est refusé. Injection documentaire contre fournisseur réel non exécutée. |
| K — agent indisponible | Aucun scénario d’agent réellement arrêté n’a été exécuté en navigateur; retour d’outil simulé seulement dans les tests existants. |
| L — accès non autorisé | En-têtes de rôle forgés rejetés (401); le registre refuse un rôle absent des permissions dans le test Python. |

## Commandes de démarrage et de test

Voir les instructions depuis environnement neuf dans [README.md](../README.md). Pour les tests racine ARGOS, utiliser `pytest -q tests`, pas la collecte globale tant que l’import du sous-projet Arthena n’est pas isolé. Les tests JavaScript utilisent Node.js. Le parcours Chromium de preuve a utilisé Playwright installé sous `/tmp`, et un shim d’identité local temporaire; ces captures ne prouvent pas l’authentification de production.

## Point de contrôle

Les preuves confirment l’interconnexion déterministe des agents et la capacité du backend à renvoyer les outils au fournisseur configuré. La démonstration exigée « vrai Gemini appelle plusieurs agents dans la même requête » reste **non validée** à cause du 503 fournisseur. Les tests globaux, les flux IoT/GPS réels et plusieurs scénarios de sécurité restent incomplets. Le point de contrôle reste assorti de ces réserves; la phase 4 ne peut pas être qualifiée de validation complète. La reprise visuelle a corrigé les KPI invisibles : JetBrains Mono n’étant pas disponible dans le navigateur de capture, les valeurs utilisent la police Inter chargée et apparaissent dans la nouvelle capture. La marque IA 3D, le bouton vectoriel, l’état vide GPS et les filtres de carte ont aussi été vérifiés en Chromium. Les réponses réelles du fournisseur Gemini restent indisponibles/non validées.
