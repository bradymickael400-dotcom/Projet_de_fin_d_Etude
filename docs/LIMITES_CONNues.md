# Limites connues — Phase 4

- Le service Gemini a renvoyé HTTP 503 pendant l’appel réel. La disponibilité, la génération Gemini et les appels réels d’outils depuis Gemini restent non validés.
- Les tests de coordination utilisent un transport LLM simulé. Ils prouvent les contrats, appels multi-agents et retours d’outils dans le code, mais pas la réussite du fournisseur externe.
- La base consultée pendant les captures renvoyait zéro position GPS et zéro conteneur via les API de carte. Aucun marqueur réel ne pouvait être affiché; le fond cartographique s’est chargé.
- Le risque est déterminé par des règles existantes; ce n’est pas un modèle ML entraîné ni une probabilité calibrée.
- Le RAG est une recherche lexicale locale sur les fichiers pris en charge. La présence, l’exhaustivité ou la validité de documents réglementaires ne sont pas garanties par les tests.
- Les parcours d’ingestion de matériel IoT, perte réelle de communication, dérive de trajet sur route attendue, incident réel et données fraîches GPS ne sont pas démontrés ici.
- Le scénario de refus hors domaine, l’injection d’instructions à l’intérieur d’un document et l’indisponibilité réelle d’un agent n’ont pas été validés de bout en bout.
- Les captures navigateur utilisent un serveur Flask temporaire de preuve qui injecte une identité superadmin locale; elles valident l’interface et les API métier locales, pas la connexion réelle ni la politique d’authentification de production.
- La suite `arthena_flask/tests` et la collecte globale restent bloquées par `flask_migrate` absent et la collision de package `app`.
- Aucun scanner Python de vulnérabilités (par exemple `pip-audit`/Bandit) n’était installé dans l’environnement. L’audit npm exécuté concernait uniquement l’outil Playwright temporaire.
- Dans la capture Chromium du tableau de bord, le DOM contient les quatre valeurs KPI retournées par l’API, mais elles ne sont pas visibles dans le PNG; certains libellés de contrôles icône sont également absents visuellement malgré leur présence DOM. La hiérarchie et la mise en page ont été reprises, mais cette anomalie de rendu reste à corriger avant de considérer la refonte visuelle terminée. Cause CSS/navigateur non confirmée.
