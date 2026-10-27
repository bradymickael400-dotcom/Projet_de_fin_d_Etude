# Interconnexion des agents ARGOS

## Registre implémenté

`app/agents/registry.py` décrit chaque capacité avec identifiant/version, mission, capacité, description, schémas d'entrée/sortie, services appelés, limites, rôles autorisés et état `registered`. Ce dernier indique que le handler est installé; il ne certifie pas la disponibilité runtime de PostgreSQL ou du fournisseur externe. L'orchestrateur et Gemini découvrent les mêmes entrées avec `AgentRegistry.discover()`. Les arguments inconnus, manquants, de mauvais type ou provenant d'un rôle non autorisé sont refusés.

| Agent | Données / responsabilité |
|---|---|
| `iot_monitor` | Dernière mesure `sensor_readings` de la boîte autorisée, horodatage, âge et qualité. |
| `gps_route` | Service `get_hybrid_position`: position, source, timestamp et fraîcheur, ou position indisponible. |
| `risk_assessor` | Appelle `iot_monitor` et `gps_route`, consomme leurs objets de résultat et retourne les signaux déterministes et les références sources. |
| `knowledge_retriever` | Recherche locale `.md`, `.txt`, `.rst`; retourne texte, chemin, lignes et score lexical. |

Les résultats partagent les champs `agent_id`, `message_id`, `timestamp`, `status`, `data`, `provenance` et `error`. Le `trace_id` corrèle la requête LLM; les IDs de résultats imbriqués montrent l'échange direct entre agents.

## Flux LLM multi-outils

`GeminiToolProvider` envoie les capacités autorisées au modèle comme déclarations de fonctions. Il traite plusieurs `functionCall` dans la même réponse, appelle chaque capacité, renvoie leurs résultats dans le dialogue, puis demande une réponse de synthèse. La boucle est bornée à quatre tours. Une fonction non enregistrée ou un appel non autorisé n'est jamais exécuté.

Si l'assistant a été ouvert depuis une boîte, son identifiant est transmis séparément et l'orchestrateur le réimpose aux outils opérationnels même si le modèle fournit un autre identifiant. Le gestionnaire de capacité revérifie ensuite les boîtes visibles pour le rôle et l'utilisateur.

## Audit et confidentialité

La migration `migrations/20261027_ai_agent_runs.sql` crée un journal qui conserve acteur, statut, agents et références, sans le texte de la question, les clés ou une chaîne de pensée. Le point de terminaison renvoie aussi `trace_id`, `agents_consulted`, `agent_results` et `sources`.

La route Gemini ignore `contextData` et `systemPrompt` transmis par le navigateur. Les mesures opérationnelles sont lues côté serveur par les capacités. Le prompt système précise que les résultats et documents sont des données non fiables et ne peuvent remplacer les instructions ou permissions.

## Preuve automatisée

`tests/test_agent_coordination.py` vérifie :

- que l'agent risque appelle deux autres agents et réutilise leurs résultats/provenances;
- qu'une réponse Gemini contenant simultanément deux appels de fonctions entraîne deux agents, renvoie leurs résultats au modèle, puis reçoit sa réponse finale;
- que la route API utilise le registre serveur, borne l'identifiant de boîte et ne transmet pas le contexte client;
- que le RAG renvoie des passages locaux avec repères de lignes.

Ces tests substituent les gestionnaires opérationnels ou le transport HTTP pour éviter d'exiger une base réelle ou un compte Gemini. Ils prouvent l'orchestration logicielle; ils ne prouvent pas le fonctionnement du fournisseur externe ou du PostgreSQL de production.
