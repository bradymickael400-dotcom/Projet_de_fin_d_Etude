# Architecture ARGOS après la phase 2

État : code de coordination implémenté; intégrations externes réelles non vérifiées. L'interface n'a pas été refondue dans cette phase.

```text
Utilisateur authentifié
  -> POST /api/ai/chat
  -> orchestrateur + registre unique de capacités
      -> iot_monitor -> sensor_readings / permissions de boîte
      -> gps_route -> service de positionnement existant (IoT/AIS/dernière position)
      -> risk_assessor -> consomme les résultats IoT et GPS
      -> knowledge_retriever -> corpus local autorisé, passages et lignes
  -> appels d'outils Gemini, réponses d'outils reprises dans le même dialogue
  -> réponse + agents consultés + sources + identifiant de trace
  -> journal ai_agent_runs
```

Le service d'ingestion opérationnel reste : source → validation/normalisation → Redis/PostgreSQL → règles et notifications → API existantes. Le LLM ne remplace pas les règles ou données, et n'a pas d'accès SQL direct. Les outils sont choisis dans le registre; le fournisseur ne peut pas demander une capacité absente de ce registre.

## Limites vérifiées

- Les tests multi-agents utilisent un fournisseur HTTP simulé : ils démontrent le protocole et l'échange de résultats, pas l'accès réel à Gemini.
- Le corpus livré ne contient pas de réglementation; il contient seulement un README d'instructions. Le RAG retourne donc aucun passage réglementaire tant que des documents approuvés ne sont pas ajoutés.
- La lecture de télémétrie et la position réelle nécessitent PostgreSQL et les schémas/identités applicables; ces intégrations n'ont pas été exécutées dans la suite unitaire.
- La migration d'audit a été ajoutée, mais l'arbre de travail ne contient pas les migrations antérieures signalées comme absentes dans l'audit initial. Il faut les restaurer avant un démarrage propre de la base.
