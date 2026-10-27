# Tests et preuves — Phase 4

Les résultats détaillés, limites et captures sont dans [PHASE4_POINT_CONTROLE.md](PHASE4_POINT_CONTROLE.md) et [VERIFICATION_FONCTIONNALITES_IA.md](VERIFICATION_FONCTIONNALITES_IA.md). Cette page résume les commandes réellement lancées le 27 octobre 2026.

## Réussis

- `PYTHONPATH=. .venv/bin/pytest -q tests` : **16 passed**. Couvre les quatre handlers, le transfert IoT/GPS vers l’agent risque, un tour LLM simulé avec plusieurs outils, deux boîtes choisies et les boîtes non choisie/non autorisée refusées, absence de sélection, refus lexical et classification de domaine simulée, RAG local et contrôles d’accès.
- `node --check` sur `core-state.js`, `data-pages.js`, `ui-navigation.js`, `auth-qr.js` et `script.js` : syntaxe valide.
- `node --test tests/js/phase3-ui.test.cjs` : **6 passed**, incluant la sélection multiple dans l’interface.
- Chromium/Playwright : dashboard et carte rendus, sélecteur multi-conteneurs affiché, contrôles et marque IA visibles; APIs de page observées en 200; aucune erreur JavaScript; pas de débordement à 390 px. La réponse de chat a été simulée pour valider le rendu du sélecteur. Le serveur de preuve injectait une identité locale et ne valide pas le login de production.
- POST Flask `/api/ai/chat` avec les vrais handlers/registre et un fournisseur d’outils local de test : 200, capacités IoT et GPS consultées avec statut `empty` sur les données présentes, trace d’audit relue en base.
- `docker compose config --quiet` : valide.
- `npm audit` du répertoire Playwright temporaire après mise à jour : zéro vulnérabilité.

## Échecs et non exécutés

- Appel réel `/api/ai/chat` au fournisseur Gemini : HTTP 503 fournisseur puis HTTP 502 ARGOS. Aucun résultat LLM réel ni tool call Gemini n’est prouvé.
- `pytest -q arthena_flask/tests` : échec de collecte `ModuleNotFoundError: flask_migrate`.
- `pytest -q` global : échec de collecte pour la même dépendance manquante et collision de package `app` entre Arthena et ARGOS.
- Scan Python `pip-audit`/Bandit : non exécuté, outils absents.
- Ingestion IoT matérielle, route attendue réelle, position réelle, question réglementaire complète, refus hors domaine et agent runtime réellement indisponible : non exécutés.

Le journal d’audit `brady.ai_agent_runs` manquait dans la base locale. La migration additive `migrations/20261027_ai_agent_runs.sql` a été appliquée et sa création confirmée avant le test de persistance réussi. Le détail de cette action et les limites figurent dans le rapport Phase 4.

Les captures de cette reprise sont [le tableau de bord](phase4/captures/tableau-de-bord-revue.png), [la carte GPS](phase4/captures/carte-gps-revue.png), [l’assistant avec sélecteur](phase4/captures/assistant-global-revue.png) et [l’assistant sur mobile](phase4/captures/assistant-mobile-revue.png). Le texte des alertes métier a été masqué dans la capture du tableau de bord.
