# Vérification des fonctions ARGOS Intelligence

Vérification réalisée le 27 octobre 2026 à partir du dépôt et des tests locaux. Ce document sépare les capacités réellement présentes des objectifs de la description technique jointe.

## Agents opérationnels actuellement enregistrés

| Agent | Fonction réellement exécutée | Résultat des tests |
|---|---|---|
| `iot_monitor` | Lit la dernière mesure IoT d’une boîte choisie, sa qualité et son horodatage. | Handler testé avec une réponse DB locale contrôlée; accès de boîte soumis au contrôle de rôle et de périmètre. |
| `gps_route` | Lit la position hybride disponible et sa source/fraîcheur. | Handler testé avec le service de position substitué; API navigateur de positions réelle testée séparément, sans position exploitable dans la base pendant la capture. |
| `risk_assessor` | Agrège les résultats des deux agents ci-dessus et applique les règles déterministes actuelles (alarme, porte, choc). | Test unitaire prouve la consommation des deux résultats; test du handler de production confirme le contrat. Ce n’est pas un score probabiliste. |
| `knowledge_retriever` | Recherche lexicale dans le corpus local et renvoie les lignes de provenance. | Recherche temporaire testée avec document local; le handler de production est testé avec son moteur de recherche substitué. |

L’orchestrateur expose les agents opérationnels uniquement quand au moins une boîte a été explicitement sélectionnée. Avec une boîte, l’identifiant choisi remplace toute autre valeur proposée par le modèle. Avec plusieurs boîtes, chaque appel doit viser un identifiant sélectionné; toute autre boîte est refusée. Le test multi-boîtes appelle les agents pour `17` et `18` dans le même tour et vérifie que `99` n’est jamais transmis.

## Matrice par rapport aux objectifs de la description

| Objectif | État vérifié dans le dépôt |
|---|---|
| Règles critiques embarquées et alarmes immédiates | Firmware et chemins IoT existants; le parcours matériel n’a pas été exécuté pendant cette vérification. |
| Validation et lecture des mesures | Présentes dans les composants IoT; `iot_monitor` lit la dernière mesure persistée, sans analyse de fenêtres temporelles. |
| Détection d’anomalies | Partielle : quelques seuils déterministes dans `risk_assessor`. Pas d’Isolation Forest, d’autoencodeur LSTM ni de score entraîné. |
| Prédiction de risque d’avarie ou de retard | Absente : aucun CatBoost/LightGBM, aucune probabilité prédictive entraînée. |
| Classification de gravité | Absente comme modèle dédié; l’agent risque ne produit actuellement que `warning` ou `undetermined` sur des signaux de règles. |
| Réduction des fausses alertes | Absente : pas de classifieur ni de boucle de validation humaine reliée à un modèle. |
| Analyse de trajet et de comportements | Partielle : lecture de position disponible, sans comparaison à une route prévue, géorepérage ou détection de détour dédiée. |
| Recommandations opérationnelles | Le LLM peut formuler une réponse à partir des résultats reçus; aucun moteur de recommandations validées, rôle cible, délai ou score de confiance n’est enregistré par un agent dédié. |
| Explicabilité ML / SHAP | Absente; les résultats déterministes exposent leur base et leurs entrées consommées. |
| Feature Store / entraînement / MLflow / surveillance de modèles | Absents. |
| API FastAPI dédiée, Redis, service MLflow | Absents de l’architecture d’exécution actuelle; les échanges passent par Flask et les capacités locales. |
| AIS, météo, congestion portuaire ou trafic externe | Non intégrés comme sources d’IA vérifiées dans ce parcours. |
| Dialogue logistique et choix de périmètre | Implémenté côté API et interface. Un classifieur Gemini sans outils ni données IoT décide du domaine avant les outils; des règles locales nomment plusieurs secteurs connus lorsque le fournisseur échoue. Le comportement sémantique a été testé avec un fournisseur simulé; Gemini externe a précédemment renvoyé 503, donc sa classification réelle reste non validée. |

Les termes de ML et MLOps cités dans la spécification constituent donc une feuille de route; ils ne sont pas revendiqués comme fonctionnels dans cette version.

## Résultats de cette passe

- `PYTHONPATH=. .venv/bin/pytest -q tests/test_agent_coordination.py` : **17 réussis**. Inclut les handlers (dépendances DB/position/RAG contrôlées par mocks), l’échange inter-agents, plusieurs agents dans un tour, l’isolation du périmètre multi-boîtes, le refus d’une boîte non autorisée, le refus hors secteur, la classification sémantique simulée et l’API sans sélection.
- `node --test tests/js/ai-assistant.test.cjs` : **3 réussis**.
- `node --check` sur `core-state.js`, `data-pages.js`, `ui-navigation.js`, `auth-qr.js` et `script.js` : syntaxe valide.
- Parcours Chromium local : carte, filtres, état vide, bulle et modal visibles; sélecteur multi-conteneurs affiché; largeur document et fenêtre identiques à 390 px; aucune erreur JavaScript. La réponse du chat a été simulée dans ce parcours visuel; la route API est validée par les tests Python.
- Capture de la carte : la base locale ne contenait aucune position GPS exploitable. Le fond cartographique dépend de tuiles externes; en cas d’indisponibilité réseau, le fond quadrillé de secours apparaît sans créer de positions fictives.
- L’appel Gemini réel antérieur au fournisseur a reçu HTTP 503 (retour ARGOS 502). La capacité du LLM externe à classifier le domaine et à effectuer des tool calls réels demeure non démontrée; l’interconnexion, le classifieur et les tours multiples sont prouvés avec un transport Gemini simulé.

## Captures

- [Carte GPS revue](phase4/captures/carte-gps-revue.png)
- [Assistant et choix multi-conteneurs](phase4/captures/assistant-global-revue.png)
- [Assistant sur mobile](phase4/captures/assistant-mobile-revue.png)
