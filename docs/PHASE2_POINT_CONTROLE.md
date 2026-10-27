# Phase 2 — Point de contrôle

Date : 27 octobre 2026. Périmètre : données opérationnelles, API LLM, RAG et échanges d'agents. L'interface a seulement été ajustée pour ne plus envoyer son contexte de mesures au LLM; sa modernisation reste hors de cette phase.

## Réalisé

- Registre versionné de capacités dans `app/agents/registry.py`.
- Agents IoT, GPS, risque et recherche documentaire locale dans `app/agents/specialists.py`.
- Contrats de résultats avec ID de message, horodatage, statut, données, provenance et erreur.
- Échange direct entre `risk_assessor`, `iot_monitor` et `gps_route`.
- Client Gemini REST avec appels d'outils multiples dans un même tour et réponses d'outils intégrées avant la synthèse.
- Route `/api/ai/chat` raccordée au registre; l'ancien `/api/ai/deepseek` réutilise le même chemin.
- `contextData` et `systemPrompt` du navigateur ne sont plus considérés comme source opérationnelle ou instruction système.
- Vérification des rôles, des boîtes visibles et de l'association boîte/voyage.
- RAG local borné qui retourne source et lignes, sans corpus réglementaire fictif.
- Migration pour tracer les appels et références sources sans conserver la question brute.

## Preuve principale

Commande exécutée : `PYTHONDONTWRITEBYTECODE=1 /tmp/argos-phase2-venv/bin/python -m pytest -q tests`.

Résultat : **4 réussis**. Le test `test_llm_one_request_invokes_multiple_agents_and_receives_results` passe par le vrai client Gemini à transport simulé. La réponse simulée appelle simultanément les outils IoT, GPS, risque et RAG. L'agent risque interroge à son tour les agents IoT et GPS; le test vérifie que les résultats remontent, que la provenance est présente et que le LLM reçoit les sorties d'outils avant sa réponse finale.

Le test de route Flask vérifie le registre serveur, l'identité, l'ID de boîte forcé côté serveur et l'ignorance du contexte opérationnel client. Le test RAG vérifie le chemin source et les lignes. Détail : [`TESTS_ET_PREUVES.md`](TESTS_ET_PREUVES.md).

## Résultats non démontrés

- Une requête réelle au service Gemini n'a pas été effectuée. La preuve fournisseur est un faux transport HTTP.
- Les requêtes SQL IoT/GPS et la migration n'ont pas été appliquées à une base de données de test ou réelle.
- Le corpus documentaire réglementaire est absent; aucune réponse de conformité sourcée n'est démontrée.
- La commande pytest globale collecte aussi la suite séparée `arthena_flask`, bloquée par `flask_migrate` absent et une collision de package `app`. Seuls les tests racine ciblés ont été exécutés.
- Les anciennes migrations présentes dans l'index Git ne sont pas dans l'arbre de travail actuel. Une installation propre ne peut donc pas être validée avant leur restauration/localisation.

## Fichiers de cette phase

`app/agents/`, `app/knowledge/`, `app/llm/`, `app/routes/dashboard.py`, `app/routes/containers.py`, `app/config.py`, `app/static/js/ui-navigation.js`, `migrations/20261027_ai_agent_runs.sql`, `tests/test_agent_coordination.py`, `requirements.txt`, `.env.example` et la documentation phase 2 sous `docs/`.

L'architecture fonctionnelle et les fondations de sécurité existantes ont été conservées. Aucun modèle entraîné ni système de décision automatique n'a été ajouté. Le travail s'arrête ici au point de contrôle 2.
