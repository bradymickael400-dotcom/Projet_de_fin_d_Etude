# Registre des risques ARGOS

Évaluation initiale au 27 octobre 2026. Les niveaux indiquent la priorité d'investigation, pas une mesure quantitative du risque en production.

| ID | Risque / preuve | Impact possible | Priorité | Réponse proposée / état |
|---|---|---|---|---|
| R1 | Dépendances Python absentes sur l'hôte; aucun test app exécuté | Défaillance non détectée, reproductibilité faible | Élevée | Préparer un environnement contrôlé et rejouer les tests avant tout changement fonctionnel. |
| R2 | Dépôt avec de nombreux changements staged/unstaged, ajouts et suppressions | Écrasement accidentel, preuve confuse | Élevée | Préserver l'état; isoler les changements avant toute refonte; consigner les fichiers touchés. |
| R3 | Aucune interconnexion d'agents, registre ou orchestrateur | Objectif multi-agent non satisfait actuellement | Élevée | Concevoir contrat/registre et preuve sans LLM en premier, après autorisation phase 2. |
| R4 | Deux routes LLM distinctes; Gemini reçoit `contextData` fourni par client | Contextes incohérents, données falsifiées ou exposées au fournisseur | Élevée | Définir source serveur, permissions, minimisation et fournisseur avant intégration. |
| R5 | Pas de RAG, corpus ou citations dans l'application | Réponses réglementaires invérifiables | Élevée | Ne pas annoncer de conseil réglementaire sourcé; établir documents, provenance, licences et tests de récupération. |
| R6 | Règles de seuil existantes pourraient être présentées comme IA prédictive | Mauvaise interprétation opérationnelle | Moyenne/élevée | Distinguer strictement règle, modèle, LLM et agent dans interface et documentation. |
| R7 | Données de position simulées présentes dans les simulateurs | Simulation confondue avec GPS réel | Élevée | Marquer la source SIMULATED dans toutes les preuves et ne pas réutiliser comme observation terrain. |
| R8 | Dépendances externes (PostgreSQL, Redis, Gemini, AIS, SMTP, IoT) non testées | Parcours incomplet ou mode dégradé non maîtrisé | Élevée | Définir tests par intégration et preuves runtime; documenter indisponibilité par dépendance. |
| R9 | CORS configure `origins: "*"` sur les API | Origines non maîtrisées lors d'exposition web | Élevée | Restreindre aux domaines attendus et vérifier comportement pré-vol; configuration actuelle observée. |
| R10 | Configurations Compose contiennent des valeurs par défaut faibles pour DB/SECRET/admin | Déploiement mal sécurisé si valeurs non remplacées | Élevée | Confirmer secrets déployés sans les afficher; rendre valeurs de production obligatoires avant exposition. |
| R11 | Création de tables à la demande en plus des migrations | Écarts de schéma et évolution difficile à suivre | Moyenne | Cartographier les tables runtime et unifier progressivement une source de migration validée. |
| R12 | Fournisseurs AIS/maritimes et fraîcheur des positions | Position ancienne ou service sans réponse interprété à tort comme actuel | Moyenne/élevée | Toujours présenter source, timestamp, âge et état indisponible; vérifier adaptateurs réels. |
| R13 | Dépendances et API des fournisseurs LLM peuvent changer ou être incompatibles | Réponses indisponibles ou erreur runtime | Moyenne | Vérifier version installée, client, modèle et mode dégradé avec mocks; aucun appel effectué ici. |
| R14 | Audio, pièces jointes et données opérationnelles peuvent contenir des données sensibles | Divulgation par stockage, logs ou fournisseur externe | Élevée | Auditer rétention, accès, chiffrement, chemins de transfert et redaction avant connexion IA. |

## Dépendances / incertitudes à lever

- Présence et version des secrets de déploiement (non divulguées ici).
- Accès aux environnements DB/Redis et disponibilité des jeux de données de test.
- Fournisseur LLM autorisé, juridiction, rétention et périmètre de données transmissibles.
- Corpus documentaire licite, stable et adapté à la juridiction métier.
- Disponibilité des tests racine dans une branche ou une copie non visible.
- Validation humaine requise pour les décisions ayant un impact sur le transport, la sécurité ou la conformité.
