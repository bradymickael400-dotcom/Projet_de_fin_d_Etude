# Compétences transport des agents ARGOS

Le registre `app/agents/registry.py` expose les capacités aux échanges LLM. ARGOS dispose maintenant de `central_africa_data` en complément des agents IoT, GPS, évaluation du risque, recherche documentaire, réglementation et intelligence portuaire.

## Compétences activées

- **Surveillance IoT** : lit la dernière mesure liée à une boîte autorisée et expose son horodatage, son âge et sa qualité disponible.
- **Analyse GPS et itinéraire** : lit la position de la boîte sélectionnée, sa source, la fraîcheur, le corridor prévu et une trace récente enrichie. Le service mesure l'écart de chaque point, signale le seuil opérationnel et fournit des segments de carte différenciés; ce score n'est pas une probabilité.
- **Évaluation déterministe du risque** : rapproche télémétrie et position; ce n'est pas une probabilité ML ni une certification de sécurité.
- **Triage des chocs de conteneurs standards** : compare le pic mesuré au seuil ARGOS configuré pour la boîte; le repli logiciel de 5 G est une règle opérationnelle, pas une valeur CSC/ISO. Un dépassement recommande une inspection et ne prouve pas un dommage. Les facteurs de charge CSC/ISO (dont le cas de gerbage à 1,8 g) ne sont pas des seuils d'impact capteur. Sans calibration, durée/axes d'accélération et inspection de l'unité, l'agent ne calcule aucune probabilité de dommage.
- **Recherche documentaire** : retourne les passages du corpus local autorisé et leur fichier/lignes.
- **Données et préparation des modèles en Afrique centrale** : `central_africa_data` met en relation les pistes de sources du texte fourni par l'équipe et le corpus documentaire ARGOS. Il distingue les statistiques agrégées, les horaires prévisionnels, les observations candidates à valider et les incidents signalés. Il expose les champs requis pour ETA, incidents et transferts, les corridors prioritaires, les besoins de gouvernance et les critères de validation. Les sources du catalogue sont des pistes non revérifiées indépendamment par cet agent.
- **Revue réglementaire contextualisée** : `transport_regulatory` repère des sources du catalogue selon les mots-clés, le mode et la juridiction lorsqu'ils sont fournis. Il réclame les éléments manquants (pays, trajet, marchandise et date) et retourne les sources avec statut `TO_VERIFY`.
- **Intelligence portuaire** : `port_intelligence` recherche les ports/terminaux connus et leurs statistiques sourcées; pour une boîte autorisée, il restitue les transitions de proximité au point de référence et les entrées/sorties des zones géographiques configurées sur l'historique du trajet.
- **Détection de proximité portuaire** : l'ingestion GPS compare les positions aux points portuaires dans un rayon indicatif configurable et notifie les personnes déjà liées à la boîte via les mécanismes de visibilité ARGOS.

## Règles pour les réponses

1. Une convention, une loi, un code obligatoire, un guide volontaire, une norme ISO et une règle interne ARGOS sont des catégories distinctes.
2. L'applicabilité dépend du territoire, des États et du corridor, du mode, de la marchandise, de l'opération, de l'édition/date et des preuves propres au dossier.
3. Une source trouvée dans le catalogue est une piste documentaire, pas une décision juridique. Le système ne doit pas conclure qu'un trajet, une entreprise, un conteneur ou un navire est conforme ou en infraction.
4. Les faits et mesures sont ceux des outils ARGOS; les conclusions incertaines sont signalées « à vérifier » et escaladées à une personne compétente.
5. Les rapports PDF listent les compétences métier disponibles, les traces réellement enregistrées et les références rattachées à l'historique. Une compétence disponible n'implique pas qu'elle a été exécutée pour ce rapport.
6. Les points portuaires de l'inventaire ne sont pas des polygones officiels. La notification signifie qu'une position GPS est proche d'un point de référence; elle ne prouve pas que le conteneur est dans l'enceinte contrôlée. Le suivi d'historique expose explicitement rayon, précision, source et statut de vérification.
7. Les chiffres de trafic conservent l'année, l'unité, l'URL et leur statut de vérification. EVP/manutentions ne signifie pas conteneurs uniques; les incidents et flux interportuaires absents ne sont ni estimés ni remplacés par zéro.
8. Pour les conteneurs standards de 20 et 40 pieds, aucune limite universelle d'accélération d'impact ni probabilité de dommage ne peut être déduite de la synthèse CSC/ISO. Distinguer le signal en G, le seuil opérationnel par boîte, la priorité d'inspection et un dommage confirmé. Voir `knowledge_base/documents/standard-container-shock-assessment.md`.
9. Les API `/api/black-boxes/{id}/route-tracking` et `/api/black-boxes/{id}/port-tracking` utilisent le même périmètre d'accès par boîte que les autres données de suivi. Le suivi des zones portuaires distingue un franchissement de polygone configuré d'une simple proximité d'un point portuaire.
10. L'inventaire régional fourni par l'équipe est un contexte de recherche documentaire. Le RAG ne modifie pas les poids des modèles. Les totaux en tonnes/EVP, indicateurs de corridor et horaires prévus ne sont pas des observations individuelles pour l'entraînement ETA.
11. Une cible ETA doit nommer l'événement exact : entrée en zone portuaire, mouillage, accostage, début des opérations, arrivée frontière, sortie douane ou livraison. Ne compare pas une prédiction à un événement différent.
12. Un dossier d'incident conserve son statut (`reported`, `investigation_ongoing`, `confirmed`, `cause_confirmed`, `inconclusive`) et sa référence probante. Une anomalie de capteur ou de trajet ne confirme ni incident ni cause.
13. Les modèles ETA, anomalies et incidents ont des cibles et des jeux d'évaluation distincts. La validation doit inclure trajets normaux et incidents confirmés lorsque la tâche le demande, une séparation temporelle et par corridor, ainsi que MAE/biais pour ETA et rappel/precision/fausses alertes pour les incidents.
14. Avant une collecte, l'agent demande de consigner l'éditeur, l'URL, l'heure d'extraction, la période, le format, la licence, les restrictions de réutilisation et les limites connues. Les extractions au niveau d'un événement requièrent autorisation, anonymisation et dictionnaire de données.

## Limites actuelles

Le catalogue n'est pas un corpus intégral des textes. La recherche réglementaire reste lexicale, les statuts et ratifications doivent être validés, et le corpus documentaire local doit être alimenté uniquement avec des documents officiels autorisés, datés et versionnés. Le rapport ARGOS soutient la revue opérationnelle; il ne remplace pas une validation juridique ni un audit de certification.

Les zones proposées dans `migrations/20261101_central_african_ports.sql` sont initialisées avec un rayon par défaut de 3 km pour les ports et 1,5 km pour les terminaux spécialisés. Ces rayons servent seulement à produire un signal de proximité de démonstration; ils doivent être remplacés par des polygones validés par chaque autorité portuaire avant tout usage de contrôle d'accès ou de sécurité.
