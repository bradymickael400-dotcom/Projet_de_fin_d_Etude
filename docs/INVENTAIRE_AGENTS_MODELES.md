# Inventaire des agents et modèles

État de référence de la phase 1, puis actualisation du code au point de contrôle 2 du 27 octobre 2026. La première table préserve l'inventaire de départ; la section d'évolution décrit les ajouts de phase 2.

| Nom / composant | Type réel | Entrées et sorties | Accès / appels | Échanges avec agents | État et preuve |
|---|---|---|---|---|---|
| ReportAI / Gemini | LLM appelé depuis une route Flask; pas un agent autonome | Message + `contextData` fourni dans la requête; texte de réponse | `app/routes/dashboard.py::ai_chat`; clé `API_KEY`, modèle `GEMINI_MODEL`, client Google | Aucun échange agent observé; pas d'outil métier appelé dans la route | Code présent; non vérifié en exécution; absence de clé/configuration ou service non prouvée. |
| Proxy DeepSeek | LLM HTTP séparé | Message utilisateur; texte brut de réponse DeepSeek | `app/routes/containers.py::ai_chat_deepseek`; `DEEPSEEK_API_KEY` | Aucun; commentaire indique qu'il n'est pas appelé par défaut par le frontend | Code présent; non vérifié; un mode sans clé renvoie un écho/message de configuration. |
| Alertes télémétrie | Moteur de règles métier | Mesures normalisées et seuils configurés; alertes/notifications | `app/modules/iot/iot_event_service.py`, appelé dans `iot_service.py` | Pas de protocole agent | Présent; seuils et déclenchements inspectés, runtime non vérifié. Ne pas désigner comme ML. |
| Validation qualité télémétrie | Validateur déterministe | JSON brut; erreur ou données validées/normalisées | `app/modules/iot/validator.py`, `normalizer.py` | Aucun | Présent dans le chemin d'ingestion; tests non exécutables dans cet environnement. |
| Positionnement hybride | Service métier, non agent | Identifiant boîte/voyage; position, source, fraîcheur ou indisponibilité | `app/services/positioning_service.py`; stockage IoT/AIS; adaptateurs maritimes | Aucun | Présent; appels externes non vérifiés; certaines méthodes Vizion de position navire renvoient explicitement `None`. |
| Modèle prédictif/anomalies | Absent du code applicatif inspecté | Sans objet | Aucun artefact/module identifié | Sans objet | Absent; les règles de seuil n'établissent pas un modèle entraîné. |
| Agent documentaire/RAG | Absent | Sans objet | Pas de corpus/index/retrieval identifié | Sans objet | Absent; pas de citations réglementaires vérifiables par l'IA. |
| Orchestrateur/registre d'agents | Absent | Sans objet | Pas de code de coordination ni contrat commun identifié | Sans objet | Absent; interconnexion multi-agents non réalisée. |

## Conclusion sur l'interconnexion

Les services communiquent via les appels Python, API et stockage du backend. Cela ne forme pas une architecture multi-agents. Aucun échange explicite entre agents, découverte de capacités, corrélation de requêtes inter-agents, politique de permissions par capacité ou journal de résultat agent n'a été repéré. Le LLM Gemini prend un contexte fourni par le client, sans demander des données aux services métier dans cette route. Le proxy DeepSeek est distinct et ne constitue pas un orchestrateur.

## Évolution de phase 2

Le code décrit ci-dessus est un constat de la phase 1. Le dépôt contient maintenant les quatre capacités et le parcours multi-outils documentés dans [`INTERCONNEXION_AGENTS.md`](INTERCONNEXION_AGENTS.md). La route Gemini utilise ce registre et ignore les données opérationnelles fournies par le navigateur. L'ancien chemin DeepSeek est devenu un alias vers le même orchestrateur.

Preuve : les tests ciblés démontrent une requête LLM simulée qui invoque simultanément télémétrie, GPS, risque et recherche documentaire; le risque consomme en plus les résultats IoT et GPS. Cela prouve le mécanisme logiciel avec un transport simulé. La disponibilité réelle de Gemini, PostgreSQL et du corpus réglementaire reste non établie.

## Informations à établir avant entraînement ou RAG

- Les volumes et la qualité des séries historiques, leur provenance et des labels fiables ne sont pas mesurés ici.
- Les documents réglementaires, licences, versions, juridictions et politique de mise à jour ne sont pas constitués dans l'application.
- Le choix d'un fournisseur de LLM et les limites d'envoi de données doivent être validés avant raccordement à des données opérationnelles.
- L'état des clés est volontairement omis; leurs noms de variables et fichiers de configuration sont les seules références nécessaires à cet audit.
