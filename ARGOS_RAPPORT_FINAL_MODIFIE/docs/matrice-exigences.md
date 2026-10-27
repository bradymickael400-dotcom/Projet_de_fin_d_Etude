# Matrice de traçabilité — hackathon AI for Good

| Exigence | Fonction ARGOS | Composant / état | Test / preuve | Rapport | Statut |
|---|---|---|---|---|---|
| Agent IA et KB | Analyse d’incident sourcée | Agent et KB absents | À démontrer : réponse avec passages cités | Architecture / IA | À faire P0 |
| Politiques, lois, mandats | Conseiller conformité | Corpus national absent | À démontrer : registre de sources officielles | Gouvernance | À faire P0 |
| Ingestion KB vectorisée Sandbox | Recherche documentaire | Absent ; accès Sandbox non vérifié | À démontrer : log d’ingestion et requête | KB | Bloqué P0 |
| Scénario incomplet et séquencé | Orchestrateur d’incident | Absent | À démontrer : scénario et audit trail | Démonstration | À faire P0 |
| Décisions auditables | Revue humaine / journal | Absent pour l’agent | À démontrer : enregistrement structuré | Gouvernance | À faire P0 |
| Alignement Y.3172 / Readiness | Architecture et analyse de capacité | Documentation initiale | À démontrer : tableau de correspondance, sans revendication de conformité | Alignement | À faire P1 |
| Chaîne IoT | Ingestion et alertes | Validation + seuils présents | Rejouer API vers stockage/événement | Architecture | Partiel P1 |
| Sécurité de démonstration | Auth, RBAC, secrets, CORS | Partiel | Vérifier env non commité, origines et refus 401/403 | Sécurité | Partiel P1 |
| Reproductibilité | Docker, scripts, tests | Compose et simulateur présents | Redémarrage propre, logs et tests | Déploiement | Partiel P1 |

Source d’exigences : [ITU AI for Good Lab Hackathon UAE](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/), consultée le 22-10-2026.

