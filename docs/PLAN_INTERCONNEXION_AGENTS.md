# Plan proposé d'interconnexion des agents

État au 27 octobre 2026 : plan mis à jour après implémentation de phase 2. Les sections « Rôles possibles » et « Chemin synchrone » décrivent la proposition initiale; les sections finales indiquent ce qui existe maintenant et ses limites.

## Principe

Réutiliser les services existants comme capacités déterministes. Un service n'est pas appelé « agent » simplement parce qu'il fournit une fonction métier. Le registre ne doit exposer que des capacités réelles, versionnées, autorisées et disponibles.

## Rôles possibles à confirmer

| Capacité/rôle candidat | Base existante | Apport et limite |
|---|---|---|
| Surveillance IoT | `app/modules/iot/iot_service.py`, `iot_event_service.py` | Exposer télémétrie validée et alertes de règles; aucune autonomie de décision. |
| GPS et trajet | `app/services/positioning_service.py`, routes trajet/télémétrie | Fournir position, source, timestamp, âge et indisponibilité; les données historiques/prévues doivent être vérifiées. |
| Risques/incidents | règles IoT et événements existants | Consolider des faits déterministes seulement après définition d'une taxonomie approuvée. |
| Recherche documentaire | Aucun composant actuel | Rôle différé jusqu'à corpus versionné et droits de réutilisation vérifiés. |
| Synthèse | Route Gemini actuelle | À refondre seulement après contrat; le LLM formule à partir de résultats autorisés et n'altère pas les données. |
| Coordination | Aucun composant actuel | Appelle uniquement les capacités inscrites et permissions vérifiées. |

Ne pas créer de modèle d'anomalies tant qu'un jeu de validation et des labels ne justifient pas son évaluation. Ne pas créer un agent artificiel pour les données absentes.

## Contrat d'échange proposé

Enveloppe commune à définir avec schéma validé par l'application :

```json
{
  "message_id": "UUID",
  "correlation_id": "UUID",
  "sender": "coordinator",
  "recipient": "iot_monitor",
  "capability": "telemetry.alerts.read",
  "requested_at": "ISO-8601 UTC",
  "subject": {"container_id": "...", "black_box_id": 0},
  "context": {"time_from": "...", "time_to": "..."},
  "data_refs": [],
  "classification": "operational",
  "status": "requested",
  "result": null,
  "error": null,
  "provenance": []
}
```

Le schéma final devra contrôler les identifiants, tailles, dates, types de résultats, provenance, statut et permissions. N'inclure un niveau de confiance que si sa méthode est définie et calibrée. Ne transmettre que des références plutôt que des blobs lorsqu'une permission peut être vérifiée au service propriétaire.

## Chemin synchrone minimal proposé

1. L'API authentifie l'utilisateur et détermine son périmètre.
2. Le coordinateur classe la demande selon une liste de capacités enregistrées; il n'accepte pas de nom de fonction arbitraire depuis le LLM.
3. Le service propriétaire contrôle à nouveau l'accès aux données et retourne faits, sources, horodatages, fraîcheur et données manquantes.
4. Les résultats sont corrélés, validés et audités.
5. Le LLM reçoit seulement les résultats autorisés nécessaires; il formule une réponse avec références et limites.
6. Une indisponibilité d'agent devient un état explicite, sans effacer les autres résultats valides.

Le partage direct agent-à-agent éventuel doit passer par une capacité documentée et un contrôle d'accès service-à-service; pas d'accès SQL transversal libre et pas de dépendances circulaires.

## Sécurité et preuves à exiger en phase 2

- Identité/version/mission/capacités/types d'entrée/types de sortie/permissions/état de disponibilité dans le registre.
- Schéma de messages validé et tests d'entrées malformées, références interdites, acteur non autorisé et agent indisponible.
- Identifiants de corrélation conservés dans les traces; pas de chaîne de pensée interne.
- Au moins un chemin démontré où une capacité consomme un résultat d'une autre sans LLM.
- Au moins une demande multi-capacité, avec services réellement appelés, données de test identifiées et audit produit.
- Réponse du LLM avec sources effectivement retournées et distinction des données manquantes.

## Questions qui restent ouvertes

Le stockage actuel est centralisé dans PostgreSQL/Redis; le besoin d'un bus asynchrone n'est pas établi. Le plus petit mécanisme synchrone doit être évalué d'abord. Le corpus, la politique de rétention, les permissions détaillées et le fournisseur LLM autorisé nécessitent des décisions avant une intégration réelle.

## État effectivement implémenté — point de contrôle 2

- Registre central des quatre capacités `iot_monitor`, `gps_route`, `risk_assessor` et `knowledge_retriever` (`app/agents/`).
- Le LLM peut appeler plusieurs capacités en une réponse d'outil, reçoit les résultats dans le même dialogue et formule ensuite sa réponse (`app/llm/gemini.py`).
- `risk_assessor` échange directement avec les agents IoT et GPS; ses sorties conservent leurs résultats et provenance.
- Les outils sont filtrés selon les rôles et le service contrôle le périmètre des boîtes. Les voyages doivent être associés à la boîte avant l'accès AIS.
- `POST /api/ai/chat` est le point d'entrée principal. `/api/ai/deepseek` reste un alias historique mais utilise désormais le même fournisseur et le même orchestrateur.
- La trace persistante de consultation est définie par `migrations/20261027_ai_agent_runs.sql`; elle n'enregistre ni question brute ni chaîne de pensée.
- Les preuves automatisées sont dans `docs/TESTS_ET_PREUVES.md`. L'appel fournisseur réel et les requêtes DB n'ont pas encore été exécutés.
