# Risques, décisions et repli

| Risque / décision | Impact | Décision actuelle | Repli / condition de clôture |
|---|---|---|---|
| Inscription et accès Sandbox non prouvés | Peut empêcher les exigences de KB Sandbox | À confirmer par l’équipe | Prototype local documenté ; ne pas le présenter comme hébergé par l’ITU. |
| Pays et corpus juridique non choisis | Recommandations non défendables | Choix à valider ; Cameroun proposé pour cohérence projet | Limiter le démonstrateur à l’incident technique sans avis réglementaire. |
| Aucune donnée étiquetée | Modèle ML non évalué | Ne pas entraîner/modéliser de précision | Règles explicables + revue humaine. |
| Données GPS sensibles | Risque vie privée | Scénarios synthétiques par défaut | Minimisation, contrôle d’accès, durée de conservation documentée. |
| Défauts de configuration | Exposition de secrets / comptes par défaut | Ne pas publier avant vérification | `.env` hors Git, clés renouvelées, CORS limité. |
| Tests manquants dans l’arbre | Démonstration non reproductible | Restaurer/localiser avant modifications larges | Tests API ciblés et procédure manuelle consignée. |

## Décisions à obtenir

1. Confirmation d’inscription et accès à l’AI for Good Sandbox.
2. Pays de référence et autorité compétente pour la KB.
3. Accord sur le scénario « incident progressif de conteneur ».

