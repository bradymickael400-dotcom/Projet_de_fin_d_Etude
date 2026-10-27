# Configuration LLM ARGOS

La phase 2 utilise Gemini comme seul fournisseur de génération dans le chemin principal et dans l'ancien endpoint DeepSeek conservé comme alias de compatibilité. L'alias utilise le même registre, les mêmes outils et la même clé Gemini; il ne contacte plus l'API DeepSeek.

Variables :

- `API_KEY` : clé Gemini côté serveur, absente du frontend.
- `GEMINI_MODEL` : modèle autorisé, défaut `models/gemini-2.5-flash`.
- `GEMINI_API_BASE_URL` : endpoint REST, défaut `https://generativelanguage.googleapis.com/v1beta`.
- `KNOWLEDGE_BASE_PATH` : dossier local des documents approuvés, défaut `knowledge_base/documents`.

Le client utilise l'API REST `generateContent`, un en-tête API key, un délai maximal de 35 secondes et au plus quatre tours d'appels d'outils. Une clé absente produit HTTP 503. Une erreur du fournisseur produit HTTP 502 avec un identifiant de trace; les détails sont dans les journaux serveur.

Les résultats d'outils sont des données non fiables. Le modèle n'accède ni directement à SQL ni à des fonctions dynamiques : les seules opérations sont déclarées par le registre et vérifiées avec le rôle courant. Les appels Gemini réels n'ont pas été effectués pendant les tests.

## Observation Phase 4

Une requête réelle a atteint le point de terminaison configuré, mais Gemini a répondu HTTP 503; le proxy ARGOS l'a convertie en HTTP 502 avec trace. Cela ne valide ni la clé, ni la disponibilité, ni les outils sur le fournisseur. Voir [les preuves Phase 4](PHASE4_POINT_CONTROLE.md). La migration de journal existe dans `migrations/20261027_ai_agent_runs.sql`; `python -m app.bootstrap` l'exécute lors du bootstrap.
