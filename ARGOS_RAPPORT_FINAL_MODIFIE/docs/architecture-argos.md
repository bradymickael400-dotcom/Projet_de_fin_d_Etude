# ARGOS — architecture vérifiée et cible

## Architecture constatée

```text
ESP32 ou simulateur (présent, matériel non vérifié)
  -> API Flask / validation de payload (code inspecté)
  -> PostgreSQL/TimescaleDB + Redis (configuration inspectée)
  -> alertes par seuils / notifications (code inspecté)
  -> interface Flask (présente ; parcours à rejouer)
```

## Architecture cible minimale du concours

```text
Télémétrie réelle ou SIMULÉE
  -> API IoT -> événements validés -> stockage
                                  -> orchestrateur de scénario
                                      -> agent opérationnel
                                      -> agent conformité (RAG)
                                              -> KB officielle versionnée
                                  -> recommandation structurée
                                  -> validation humaine
                                  -> journal de décision et citations
```

### Contrat minimal de décision

`scenario_id`, `event_ids`, `status`, `facts`, `missing_data`, `sources[{document_id,url,chunk_id}]`, `recommendation`, `human_review_required`, `uncertainties`, `agent_version`, `timestamp`.

Ne jamais stocker une chaîne de pensée interne. Conserver seulement l’explication contrôlable, les faits et sources récupérées.

### Choix technique

Ne pas introduire un modèle entraîné de détection avant données de référence. Les seuils actuels sont plus explicables pour le MVP. Une KB RAG et l’orchestration doivent d’abord démontrer provenance, récupération, incertitude et revue humaine.

