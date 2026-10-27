# Référentiel des sources et historique de décisions ARGOS

Mise en œuvre initiale : 27 octobre 2026. Le registre PostgreSQL `regulatory_sources` est initialisé par `migrations/20261028_regulatory_history.sql` et `migrations/20261028_regulatory_sources_extension.sql`. Il comporte des règles internes ARGOS et un premier ensemble de 31 références nationales, CEMAC, UA, ONU/UNECE, OMI et ISO repérées dans la base jointe.

## Ce qui est enregistré

| Objet | Historique conservé |
|---|---|
| Réponse et agents IA | Trace, boîte analysée, agent consulté, action, statut/résultat, réaction IA, références source et remarques structurées. |
| Alertes de seuil IoT | Seuil interne ayant déclenché l’alerte, mesure source, séquence/appareil et réaction créée. |
| Changement de seuil | Auteur, valeurs de seuil configurées et référence à la règle ARGOS interne. |
| Déstockage | Demande, votes, décision collective, exécution différée et rapport produit. |
| Rapports conteneur | Export lié au dossier; le PDF contient l’historique et les références connues, ou signale l’absence de disposition déterminée. |
| Inventaire PDF et contrat PDF téléchargé | Événement de génération relié à une règle interne et statut d’applicabilité non évalué. |

La page Événements permet d’ouvrir le catalogue et l’historique du dossier d’une boîte. Les réponses IA exposent également les sources et leur statut dans le panneau d’assistant.

## Règles d’interprétation

- Les sources internationales et nationales ont des types séparés : traité, loi, règlement, code, norme volontaire ou source interne.
- `legal_status` décrit l’état documentaire ou le contrôle restant. Il ne suffit jamais à établir l’applicabilité à un trajet ou une cargaison.
- La recherche de sources est lexicale et donne des pistes, pas un moteur d’applicabilité juridique. Elle ne vérifie pas automatiquement ratification, amendements, champ matériel, territoires, contrat ou dates.
- Une référence interne ARGOS n’est pas une loi. Un résultat capteur n’est pas une preuve autonome de conformité. Les réponses doivent demander les faits manquants et faire apparaître « à vérifier ».
- Les normes ISO ne sont ni intégralement reproduites ni certifiées par ARGOS. Vérifier édition, licence et contrat auprès du catalogue officiel.
- Les identifiants `source_key` liés aux événements sont stockés en JSONB. Les traces sont auditables par application mais ne sont pas cryptographiquement immuables; le scellement blockchain actuel est un système distinct.

## API

- `GET /api/regulatory/sources?q=SOLAS&jurisdiction=Cameroun&mode=road` retourne les notices de référence disponibles à l’utilisateur authentifié.
- `GET /api/regulatory/history?box_id=17` retourne les événements d’historique du dossier après vérification du périmètre d’accès à la boîte.

Les deux endpoints n’autorisent pas une conclusion de conformité. Toute règle légale retenue dans un workflow métier doit encore être vérifiée par une personne compétente avec les informations du trajet réel.

## Sources prioritaires enregistrées

- Cameroun : loi 2024/017 sur les données personnelles, loi 2023/010 sur le ferroviaire, lois et portails de cybersécurité/communications/transport routier.
- Maritime/containers : SOLAS, VGM (SOLAS VI/2), MARPOL, CSC, IMDG, CTU Code.
- Routier : CMR, ADR, TIR et instruments CEMAC à vérifier par corridor.
- Ferroviaire : COTIF, avec participation des États à établir.
- Afrique : Charte africaine révisée du transport maritime et statut de ratification à vérifier.
- Management volontaire : ISO/IEC 27001, ISO 28000, ISO 39001 et ISO 22301.

Le corpus RAG en texte intégral n’est pas fourni par ces notices. Les conditions de licence, le texte consolidé officiel et les extraits/articles pertinents doivent être récupérés et validés avant d’utiliser ces notices comme réponses juridiques.

## Vérifications exécutées le 27 octobre 2026

| Vérification | Résultat réel | Portée |
|---|---|---|
| `./.venv/bin/python -m pytest -q tests` | 17 réussis | Tests API, sécurité, orchestration et agents. Le fournisseur Gemini est simulé dans les tests d’orchestration. |
| `node --test tests/js/phase3-ui.test.cjs` | 6 réussis | GPS, filtres carte, assistant global, sélection explicite de plusieurs boîtes, références, échanges inter-agents et marque ARGOS 3D. |
| `docker compose config --quiet` | Réussi | Configuration Compose valide. |
| GET local `/` et GET public `/` | HTTP 200 chacun | Page servie sur `http://localhost:5002/` et via le tunnel public actif communiqué séparément. |
| État des conteneurs Compose | Web sain; DB saine; worker, Redis et tunnel actifs | Contrôle de disponibilité des services après redémarrage. |
| Intégration API avec identité de test et fournisseur LLM simulé | Catalogue, recherche, carte, chat, historique et PDF ont répondu; événements de test supprimés | Exercice Flask/PostgreSQL de bout en bout, sans identité ni données réelles de client. |

Le test JavaScript simule les nœuds DOM du navigateur; aucune session de navigateur interactive réelle n’a été exécutée pendant cette vérification. Les captures déjà présentes dans `docs/phase4/captures/` documentent les vues de l’interface, mais ne constituent pas un test d’interaction en direct.

La variable `GEMINI_API_KEY` est absente du conteneur au moment de la vérification. Le passage au service Gemini externe et sa génération avec la clé de déploiement ne sont donc pas validés. Les tests montrent que l’orchestrateur appelle plusieurs agents dans une même requête, transmet leurs résultats au fournisseur, et que l’agent d’évaluation consomme les sorties des agents télémétrie et GPS; ils ne prouvent pas la disponibilité du modèle externe.
