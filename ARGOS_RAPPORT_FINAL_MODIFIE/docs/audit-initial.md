# ARGOS — audit initial vérifiable

Date : 22 octobre 2026. Périmètre inspecté : dépôt parent ARGOS, configuration Docker, firmware, simulateur et documents AI for Good disponibles localement. Les composants hors de cet environnement ne sont pas déclarés opérationnels.

| Élément | État réel | Preuve observée | Écart | Priorité | Action nécessaire |
|---|---|---|---|---|---|
| API IoT | VALIDÉ dans le code | `app/modules/iot/validator.py` valide UUID, horodatage, bornes GPS et capteurs | Exécution bout en bout à rejouer | P1 | Ajouter une procédure reproductible et conserver le journal. |
| Alertes capteurs | PARTIEL | `iot_event_service.py` applique des seuils température, humidité, choc, pression et vitesse | Ce sont des règles, pas un modèle IA mesuré | P1 | Formaliser la gravité et le retour de revue humaine. |
| Stockage / diffusion | PARTIEL | Compose déclare PostgreSQL/TimescaleDB et Redis | Persistance non rejouée dans cet audit | P1 | Rejouer une télémétrie puis vérifier les enregistrements. |
| Plateforme Docker | VALIDÉ précédemment, à revalider | HTTP 200 observé le 13-10-2026 ; `docker-compose.yml` inspecté | Pas de test relancé ce jour | P1 | Exécuter le démarrage et noter les versions. |
| Firmware ESP32 | NON VÉRIFIÉ | `firmware/argos_esp32/argos_esp32.ino` présent | Aucun journal de matériel connecté | P2 | Tester sur appareil ou utiliser un simulateur étiqueté. |
| Simulateur | PARTIEL | `scripts/simulate_argos_box.py` présent | Scénarios et résultats non exécutés ici | P1 | Créer des scénarios synthétiques traçables. |
| Détection IA / risque | ABSENT | Aucun modèle, entraînement ou métrique trouvé | Les seuils ne répondent pas à toutes les fonctions IA annoncées | P1 | Conserver les règles comme MVP ; collecter des labels avant ML. |
| Agent RAG / KB vectorielle | ABSENT | Aucun composant d’ingestion, embedding ou récupération trouvé | Exigence centrale du hackathon | P0 | Construire corpus, ingestion, récupération citée et journal d’agent. |
| Journal de décision agent | ABSENT | Aucun schéma ou log de sources/décisions identifié | Auditabilité insuffisante | P0 | Créer un journal structuré sans chaîne de pensée interne. |
| Authentification et RBAC | PARTIEL | Jetons, RBAC et clés appareil hachées inspectés | CORS permissif et valeurs Compose par défaut | P1 | Externaliser secrets et limiter les origines avant exposition. |
| Tests automatisés | NON VÉRIFIÉ | Aucun fichier sous `../tests/` visible malgré l’index Git | Tests non exécutables depuis l’arbre présent | P1 | Restaurer/localiser les tests ou écrire des tests ciblés. |

## Faits de concours à ne pas confondre

Le hackathon demande une solution à agents, une KB issue de documents liés au cas d’usage, une analyse de politiques, un scénario progressif et des traces auditables. Voir la [page officielle](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/). L’alignement avec [ITU-T Y.3172](https://www.itu.int/rec/T-REC-Y.3172-201906-I/en) est un critère demandé ; ce n’est pas une certification automatique.

