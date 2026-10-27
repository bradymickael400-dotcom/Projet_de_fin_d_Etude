# Feuille de route indicative sur sept jours

Ce plan est une estimation initiale fondée sur le dépôt observé le 27 octobre 2026. Il ne constitue ni engagement de livraison ni autorisation de passer aux phases ultérieures. Les dépendances de services et l'état Git devront être clarifiés avant chiffrage fiable.

| Jour | Objectif | Travail proposé | Critère de sortie / dépendances |
|---|---|---|---|
| 1 | Reproductibilité et socle | Préparer environnement Python/Docker; exécuter migrations et tests existants; inventorier les permissions et les routes IA; identifier les changements de travail préexistants à préserver. | Démarrage reproductible, versions et état initial consignés. Dépend de l'accès DB et dépendances. |
| 2 | Contrat des capacités | Définir enveloppe de message, registre minimal, provenance et permissions; mapper services réutilisables IoT, position et règles. | Schéma validé et tests de contrat; aucune nouvelle capacité fictive. |
| 3 | Première capacité IoT | Envelopper lecture d'alertes/mesures existantes dans une interface accessible au coordinateur; tester autorisation, absence et données périmées. | Résultat structuré avec sources et âge; nécessite données d'essai isolées. |
| 4 | Première capacité géospatiale et coordination | Réutiliser positionnement existant; coordonner deux capacités via appel synchrone; gérer erreurs et corrélation. | Démonstration inter-capacité sans LLM et trace d'audit. |
| 5 | Couche LLM et base documentaire, si corpus disponible | Clarifier/remplacer les deux appels LLM séparés; définir accès outil; ingestion/citations seulement avec documents autorisés et provenancés. | Réponse fondée sur outils/sources réels; sinon documenter le blocage sans fausse démo. |
| 6 | API/UI minimale et sécurité | Exposer un endpoint coordonné, connecter l'interface existante si faisable, contrôler permissions, limites et indisponibilités. | Parcours observable sans clés côté client; revue de sécurité ciblée. |
| 7 | Validation et dossier de preuves | Tests unitaires/intégration et scénarios normal, alerte, données manquantes, refus accès, agent indisponible; rapporter résultats/limites. | Toutes les affirmations rattachées à preuves; tests bloqués/non exécutés clairement signalés. |

## Réserves de calendrier

- L'environnement d'audit n'avait pas les dépendances Python applicatives et aucune stack n'a été démarrée.
- La connexion aux fournisseurs Gemini, DeepSeek et maritimes, au réseau, au matériel et aux données réelles n'est pas prouvée.
- Corpus réglementaire validé, permissions métier, métriques qualité et disponibilité des données d'essai restent des prérequis.
- Sept jours peuvent suffire à un démonstrateur ciblé si ces prérequis sont levés; ils ne garantissent pas une plateforme IA complète prête pour la production.
