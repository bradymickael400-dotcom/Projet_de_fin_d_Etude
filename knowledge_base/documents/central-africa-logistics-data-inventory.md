# Inventaire des données logistiques d’Afrique centrale — ARGOS

> Provenance : texte de recherche fourni par l’équipe ARGOS le 29 octobre 2026. Les organismes, liens, chiffres et événements ci-dessous sont des références documentaires à vérifier dans leur source primaire avant tout usage opérationnel ou publication. Les chiffres agrégés ne sont pas des observations individuelles. Les incidents signalés ou faisant l’objet d’une enquête ne sont pas des incidents confirmés ni des causes établies. Les données synthétiques et les hypothèses de corridor ne constituent pas des traces GPS terrain.
>
> Usage dans ARGOS : document de contexte consultable par l’agent de recherche documentaire. Ce fichier n’est pas un dataset d’entraînement du classificateur de capteurs ou d’ETA : il ne contient pas les enregistrements temporels structurés, les variables capteurs et les étiquettes confirmées nécessaires à ces tâches. Chaque observation future devra conserver sa source, sa date de collecte, sa licence, sa géographie et son statut de validation.

---

# 6. Données propres à l'Afrique centrale : inventaire par pays

Pour ARGOS, il faut distinguer les données relatives aux ports, les trajets maritimes, le transport terrestre et ferroviaire, les incidents et les heures réellement constatées.

J'ai identifié des sources spécifiques à plusieurs pays d'Afrique centrale. Voici les ressources à exploiter, en indiquant précisément ce que chacune peut fournir et ce qui reste à obtenir.

## Cameroun

## Port de Kribi

Statistiques exportables

L'Autorité portuaire de Kribi publie des séries statistiques sur les escales de navires, les conteneurs en EVP, les tonnages de marchandises et le trafic de transit. La page comporte des options d'export CSV et Excel. Les séries visibles incluent des années allant de 2018 à 2023 pour certains indicateurs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pak.cm\&sz=32)

Port Authority of Kribi



[Ouvrir les statistiques du Port de Kribi](https://pak.cm/en/apropos/trade-statistics/?utm_source=chatgpt.com)

À obtenir en priorité : les fichiers exportés d'escales et de trafic, puis les journaux opérationnels avec les heures d'arrivée et de départ réellement enregistrées.

## Ports de Douala et Kribi — Conseil national des chargeurs du Cameroun (CNCC/CNSC)

Le bulletin statistique du premier trimestre 2025 documente les flux de marchandises associés aux ports de Douala et de Kribi, à partir des déclarations de suivi électronique du fret. Il indique notamment 3 357 000 tonnes de trafic maritime hors pétrole brut pour le trimestre. Il s'agit d'une statistique agrégée, pas de 3,357 millions de tonnes d'observations individuelles.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.cncc.cm\&sz=32)

BOS_2025_T1 ENGLISH



[Télécharger le bulletin statistique du premier trimestre 2025](https://www.cncc.cm/uploads/media/publication/0001/04/625c0efd20e57234ee53d4776dd351a2808b93da.pdf?utm_source=chatgpt.com)

À demander : les données détaillées des déclarations de suivi électronique du fret, les événements d'acheminement et les heures horodatées, sous réserve d'autorisation et de disponibilité.

## République du Congo

## Port autonome de Pointe-Noire

Dates et heures d'escales publiées

Le site officiel du port publie un tableau de programmation des navires et des navires à quai, avec des colonnes consacrées au nom du navire, au consignataire, au type, au quai, aux dates et heures d'arrivée et de départ, ainsi qu'à la provenance et à la destination.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://papn-cg.org\&sz=32)

Port Autonome de Pointe-Noire



[Consulter le tableau des navires à quai](https://papn-cg.org/programmation-des-navires-navires-a-quai/?utm_source=chatgpt.com)

Limite importante : le tableau public mélange des horaires et des événements d'escale, et certaines lignes peuvent comporter des incohérences de dates. Il faut vérifier chaque ligne et demander les journaux de mouvements du port avant de considérer les heures comme des observations de référence validées.

L'Organisation maritime internationale a par ailleurs mené une mission d'évaluation en mai 2026 pour préparer la mise en place d'un guichet unique maritime à Pointe-Noire. Ce travail institutionnel constitue une piste pour identifier les organismes détenant les données d'arrivée, de séjour et de départ.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.imo.org\&sz=32)

Organisation Maritime Internationale



[Lire le compte rendu de l'OMI](https://www.imo.org/fr/mediacentre/pages/whatsnew-2454.aspx?utm_source=chatgpt.com)

## République démocratique du Congo (RDC)

## Office de gestion du fret multimodal (OGEFREM)

Horaires prévisionnels disponibles

L'OGEFREM publie une page d'horaires de navires desservant le port de Matadi, avec les compagnies, les provenances et les dates d'arrivée prévues. La page consultée affiche notamment des dates de juin 2025. Ces données sont des arrivées prévues, pas des arrivées réellement constatées.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.ogefrem.cd\&sz=32)

Ogefrem



[Consulter les horaires des navires vers Matadi](https://www.ogefrem.cd/services/horaires.html?utm_source=chatgpt.com)

À demander : les manifestes d'escales historiques, les heures d'arrivée au point de pilotage, les heures d'accostage et de départ, ainsi que les journaux d'incidents et de transfert multimodal.

## Gabon, Guinée équatoriale, Tchad et République centrafricaine

Pour ces pays, je n'ai pas vérifié dans cette recherche un jeu public complet contenant simultanément des trajectoires individuelles, des heures d'arrivée réelles et des incidents confirmés. Je ne vais donc pas prétendre que ces jeux de données sont disponibles.

Des points d'entrée à explorer sont :

| Pays                      | Organismes et données à cibler                                                                                              |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Gabon                     | Office des ports et rades du Gabon, autorités portuaires d'Owendo, journaux d'escales et incidents                          |
| Guinée équatoriale        | Autorités portuaires de Malabo et Bata, journaux d'escales et événements de transport                                       |
| Tchad                     | Ministère des Transports, Douanes et opérateurs du corridor N'Djamena–Douala, heures de passage et événements routiers      |
| République centrafricaine | Ministère des Transports, Douanes et opérateurs du corridor Bangui–Douala/Kribi, heures de passage, transferts et incidents |
| RDC                       | OGEFREM, autorités portuaires de Matadi et Boma, opérateurs fluviaux et ferroviaires                                        |

Ces noms sont des pistes institutionnelles à contacter, pas la confirmation qu'ils mettent actuellement des fichiers individuels à disposition du public.

## 7. Source régionale importante : incidents maritimes confirmés ou signalés

J'ai identifié une source particulièrement pertinente pour ton besoin : le Centre régional de sécurité maritime de l'Afrique centrale (CRESMAC). Son registre public publie des événements datés, des positions, des catégories d'incidents et des descriptions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.cresmac.org\&sz=32)

CRESMAC



## Incidents réels documentés dans le registre public du CRESMAC

Extraits de dossiers publiés dans le registre consulté ; les qualifications ci-dessous distinguent les faits rapportés des causes qui restent à établir.

1\. Naufrage du MV LK VICTORIA — 22 mai 2024

- Zone : au large de Limbe, sur la route vers Malabo.
- Position géographique : le registre situe l'événement à environ 13 milles nautiques du port d'escale, sans fournir dans l'extrait une coordonnée exacte.
- Bilan publié : 9 rescapés et 1 disparu.
- Cause rapportée : mauvais état de la mer.
- Source : [Registre des incidents du CRESMAC](https://www.cresmac.org/incidents?utm_source=chatgpt.com).&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://www.cresmac.org\&sz=32)

  CRESMAC



Qualification pour ARGOS : naufrage rapporté par une source institutionnelle régionale. Pour entraîner un classificateur de causes, il faut obtenir le rapport d'enquête avant de traiter la cause comme définitivement confirmée.

2\. Approche suspecte visant le MV MAERSK PARAISO — 5 juin 2024

- Zone : à environ 32 milles nautiques des côtes gabonaises.
- Position publiée : 02°33′ S, 009°05′ E.
- Trajet rapporté : Bata, Guinée équatoriale, vers Pointe-Noire, République du Congo.
- Événement : approche suspecte d'une embarcation ; le navire aurait modifié sa vitesse et son cap, après quoi la poursuite aurait cessé.
- Source : [Registre du CRESMAC](https://www.cresmac.org/incidents?utm_source=chatgpt.com).&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://www.cresmac.org\&sz=32)

  CRESMAC



Qualification pour ARGOS : événement de sécurité signalé, mais pas nécessairement une attaque confirmée. Il faut préserver le libellé original et le niveau de certitude.

3\. Collision du MV SEA HONOR et du MV BLACK RHINO — juillet 2026

- Zone : chenal du port de Douala-Bonabéri, Cameroun.
- Période : nuit du 11 au 12 juillet 2026.
- Source : communiqué du ministère camerounais des Transports, publié le 21 juillet 2026.
- État de l'enquête : le ministère a annoncé une démarche destinée à examiner les circonstances et les causes de l'accident.&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://mintransports.cm\&sz=32)

  Ministère des Transports



Source officielle : [Communiqué du ministère des Transports](https://mintransports.cm/espace-presse/actualit%C3%A9s-du-mint/collision-entre-les-navires-mv-sea-honor-et-le-mv-black-rhino-le-mint-en-visite-de-travail-%C3%A0-douala.html?utm_source=chatgpt.com)

Ces trois cas constituent des observations documentaires réelles exploitables pour construire un registre d'incidents, sous réserve de conservation des sources et de vérification des rapports. Ils ne constituent pas, à eux seuls, un jeu de données suffisant pour entraîner un modèle général de prédiction d'incidents.

Pour élargir le registre, l'Organisation maritime internationale donne accès au module Marine Casualties and Incidents de GISIS, avec des recherches par événement et des rapports d'enquête accessibles au public après création d'un compte. Certains contenus sont réservés aux États membres.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.imo.org\&sz=32)

Organisation Maritime Internationale+1



- [GISIS — Organisation maritime internationale](https://gisis.imo.org/?utm_source=chatgpt.com)
- [CRESMAC — incidents maritimes régionaux](https://www.cresmac.org/incidents?utm_source=chatgpt.com)

Règle pour l'entraînement : conserve au minimum les états `signalé`, `enquête_en_cours`, `confirmé`, `cause_confirmée` et `non_concluant`. Ne transforme pas automatiquement un événement signalé en incident confirmé.

## 8. Données réelles de corridors terrestres en Afrique centrale

Pour ARGOS, les trajets ne doivent pas être limités aux navires. Les marchandises transportées par conteneur passent également par les corridors routiers et parfois ferroviaires.

La Banque mondiale a publié en juin 2026 un programme de modernisation du corridor Douala–Bangui. Le document décrit un corridor de plus de 1 400 km, des temps de trajet annoncés de 9 à 12 jours dans des conditions normales et 38 points de contrôle au Cameroun, dont 17 associés à des paiements informels selon le communiqué.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.worldbank.org\&sz=32)

Banque mondiale



Ces chiffres sont des indicateurs publiés à l'échelle du corridor, pas les observations individuelles de chaque camion.

Corridors prioritaires à instrumenter

[WATITI EXPRESS — Votre partenaire logistique de confiance au Cameroun](https://images.openai.com/static-rsc-4/AiOB-NijPkkGhApTo38SFy9GumMWmOaNqBPvNsf_4xk7xFoK-tl0OmpaZj8exx240wNVlh0XTIxBxdVxfpHgLFgf8jAhTD8ItyEqvqaICm6B3T83-uH6XbWn4oLKEmfz_YDB3RTO6CJJqRQqev8Tjrj425eB_cSteFqaWJyDJAM?purpose=inline)

Douala–Ngaoundéré–N'Djamena

Cameroun et Tchad. À documenter : sortie du port, passages de postes de contrôle, étapes de transport, frontières et livraison finale.

[Transit Douala-Bangui 2026 : T1, TTU, Coûts & Délais · ALC](https://images.openai.com/static-rsc-4/Lq2Qki02Qe2zBP-0L1nU_zBAt9NpWul1kWnIbqPThXIXdHaMMuV8UL4ukWbFXs8PxZK0OfHNWgprDLc76cBxRkyANL0BYkyUGztSobU9pP-UVc1M5gBJTjl9RO1a13iKbx0hsgNnRAYAUYzl8Jpe55wp5to2M-g51_IV_aNZW_Q?purpose=inline)

Douala–Bangui

Cameroun et République centrafricaine. À documenter : temps réel de parcours, immobilisations, incidents routiers, délais douaniers et transferts de responsabilité.

[Programme d’urgence du Port Autonome de Pointe-Noire - Catram consultants by Inddigo](https://images.openai.com/static-rsc-4/SIkp0sCWkQWs1oE35sSqOH8xbFfYjyq0LGGnTIrIf_z_1pilg3vF9d7SsdwmL9vuoG0eeEKB3v96KGyV6axJkntb56HpbkK1XpEF-VFv2-aS_88aZlRXySxTANOtIN69PUm4vNf1TIroxf0EviUaE9eM2k-64GlamuQO0tsdYnU?purpose=inline)

Pointe-Noire–Brazzaville et liaisons régionales

République du Congo, avec connexions vers d'autres pays de la région. À documenter : escales, opérations de terminal, étapes ferroviaires et routières, et remises de marchandises.

Pour établir une référence historique, l'OCDE publie également des indicateurs de corridors d'Afrique centrale, dont des temps de parcours et de franchissement de frontières observés sur des périodes antérieures. Ces indicateurs servent à comprendre les problèmes logistiques et à établir des hypothèses, mais ils ne remplacent pas les données brutes nécessaires à l'entraînement.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.oecd.org\&sz=32)

OECD+1



- [Banque mondiale — corridor Douala–Bangui](https://www.worldbank.org/en/news/press-release/2026/06/12/world-bank-approves-us-1-12-billion-program-to-modernize-the-douala-bangui-economic-corridor?utm_source=chatgpt.com)
- [OCDE — corridors d'Afrique centrale](https://www.oecd.org/en/publications/africa-s-development-dynamics-2025_c2b40285-en/full-report/infrastructure-and-productive-transformation-in-central-africa_46f19eb4.html?utm_source=chatgpt.com)

## 9. Toutes les données à collecter pour entraîner les modèles d'ARGOS

Je recommande de constituer un jeu de données unifié, mais de ne pas entraîner un seul modèle à faire toutes les tâches. Chaque compétence d'ARGOS doit disposer de ses propres données d'apprentissage et de ses propres critères de validation.

### A. Trajectoires réelles et prédiction des heures d'arrivée

| Champ                   | Contenu attendu                                                | Source à solliciter                          |
| ----------------------- | -------------------------------------------------------------- | -------------------------------------------- |
| `trip_id`               | Identifiant pseudonymisé du trajet                             | Transporteur ou opérateur                    |
| `vehicle_id`            | Identifiant pseudonymisé du navire ou véhicule                 | Opérateur ou fournisseur AIS                 |
| `timestamp_utc`         | Horodatage exact de chaque position                            | AIS, GPS ou journal de bord                  |
| `latitude`, `longitude` | Position mesurée                                               | AIS/GPS                                      |
| `origin`, `destination` | Origine et destination documentées                             | Manifeste, réservation ou ordre de transport |
| `eta_original`          | Heure d'arrivée estimée initialement                           | Système opérationnel                         |
| `eta_updates`           | Historique des estimations successives                         | Système opérationnel                         |
| `arrival_observed`      | Heure réelle d'arrivée, avec définition précise de l'événement | Journal du port ou preuve de livraison       |
| `departure_observed`    | Heure réelle de départ                                         | Journal du port ou du transporteur           |
| `delay_reason`          | Motif documenté du retard, si connu                            | Rapport opérationnel                         |

Attention : pour les navires, l'arrivée dans la zone portuaire, l'arrivée au mouillage, l'accostage et le début des opérations sont quatre événements distincts. Pour un camion, l'arrivée à la frontière, la sortie de douane et la livraison sont également distinctes. ARGOS doit prédire l'événement exact visé.

### B. Incidents réels et confirmation des causes

Chaque ligne doit correspondre à un événement documenté, pas à une anomalie artificiellement créée.

| Champ                 | Contenu                                                     |
| --------------------- | ----------------------------------------------------------- |
| `incident_id`         | Identifiant unique                                          |
| `event_time`          | Date et heure documentées                                   |
| `event_location`      | Coordonnées ou lieu vérifié                                 |
| `asset_id`            | Navire, camion, conteneur ou équipement concerné            |
| `incident_type`       | Collision, panne, naufrage, intrusion, avarie, retard, etc. |
| `severity`            | Niveau de gravité selon le référentiel retenu               |
| `confirmation_status` | Signalé, enquête en cours, confirmé ou non concluant        |
| `cause`               | Cause retenue par une source compétente, si disponible      |
| `evidence_reference`  | Référence du rapport, communiqué ou dossier                 |
| `source_timestamp`    | Date de publication ou de dernière mise à jour de la source |

Pour les incidents rares, conserve aussi les trajets sans incident. Sans ces exemples négatifs, un modèle risque de classer tous les trajets comme dangereux.

### C. Transferts et gouvernance

Pour chaque transfert entre acteurs ou modes de transport, demande :

- l'identifiant de l'expédition et du conteneur ;
- le point et l'heure de remise ;
- l'heure de prise en charge par l'acteur suivant ;
- l'état du scellé et du conteneur ;
- le document ou la signature attestant la remise ;
- les écarts de temps, les réserves et les incidents déclarés ;
- le rôle de chaque organisation dans la validation et la correction des données.

Ces informations sont nécessaires pour mesurer les temps d'attente, identifier les ruptures de traçabilité et éviter d'attribuer à un transporteur un retard survenu chez un autre acteur.

## 10. Comment transformer les données en compétences pratiques pour ARGOS

Compétence 1 — Reconstruire les trajets

- Nettoyer les coordonnées GPS/AIS et les horodatages.
- Détecter les données manquantes, doublons et positions impossibles.
- Reconstruire les segments de trajet et les escales.
- Calculer la vitesse, les arrêts et les durées observées.

Résultat attendu : un historique de trajectoires vérifiées, avec la provenance de chaque observation.

Compétence 2 — Prédire les heures d'arrivée

Commencer par une référence simple : durée historique médiane par corridor et catégorie de transport. Ensuite, tester un modèle de régression tel que LightGBM ou CatBoost lorsque le volume et la qualité des données le permettent.

Mesures : MAE en minutes ou heures, biais de prédiction, erreur par corridor et taux d'arrivées prévues dans les marges de tolérance.

Résultat attendu : une prédiction comparée à l'heure réellement observée, et non à une ETA déjà prédite par un autre système.

Compétence 3 — Détecter les anomalies

Entraîner un Isolation Forest sur des caractéristiques de trajet et de télémétrie dont les unités et les plages normales sont documentées : vitesse, arrêts, écarts d'itinéraire, chocs et température, par exemple.

Limite : une anomalie n'est pas automatiquement un incident. Le modèle doit produire un score et une explication, puis être évalué sur des incidents réels confirmés et des situations normales.

Compétence 4 — Classifier les incidents

Utiliser les dossiers documentés pour construire des étiquettes de gravité et de type d'incident. Séparer les événements confirmés des événements simplement signalés.

Commencer par un modèle interprétable, puis comparer ses résultats à des règles expertes. Évaluer notamment le rappel des incidents graves, la précision et le taux de fausses alertes.

Compétence 5 — Expliquer les alertes avec un RAG

Indexer les rapports d'incidents, les normes, les procédures et les documents de gouvernance. Le système RAG doit fournir des explications sourcées et distinguer les faits documentés des hypothèses.

Le RAG ne remplace pas un modèle de prédiction et ne doit pas inventer des preuves ou des causes.

## 11. Plan concret d'acquisition des données en Afrique centrale

Je te conseille de procéder par étapes, afin de ne pas acheter des données coûteuses avant d'avoir identifié les lacunes.

1. Étape 1 — Extraire les données publiques immédiatement disponibles. Télécharger les statistiques du Port de Kribi, collecter les escales publiées par Pointe-Noire, consulter les horaires de Matadi et archiver les incidents documentés du CRESMAC.
2. Étape 2 — Constituer un registre des sources. Pour chaque fichier, conserver l'URL, l'organisme producteur, la période couverte, la date d'extraction, le format, les droits d'utilisation et les limites connues.
3. Étape 3 — Adresser les demandes institutionnelles. Priorité au Port autonome de Douala, au Port autonome de Kribi, au Port autonome de Pointe-Noire, à l'OGEFREM et au CRESMAC. Demander les journaux détaillés, pas uniquement les rapports statistiques.
4. Étape 4 — Obtenir un échantillon pilote. Demander un extrait anonymisé couvrant un corridor et une période définis. Vérifier le nombre de trajets complets, les horodatages, la qualité des identifiants et la disponibilité des incidents confirmés avant toute acquisition plus large.
5. Étape 5 — Obtenir les données commerciales manquantes. Si les historiques AIS, les événements de conteneurs ou les ETA observées ne sont pas disponibles publiquement, demander un devis à un fournisseur et négocier les droits de stockage, d'entraînement et d'utilisation dans ARGOS.
6. Étape 6 — Construire une validation régionale. Commencer par le corridor Douala–Bangui ou Douala–N'Djamena, mesurer les performances, puis élargir à Pointe-Noire, Matadi, Owendo, Malabo et Bata lorsque les données correspondantes sont effectivement obtenues.

## 12. Modèle de demande de données à adresser aux organismes

Madame, Monsieur,

Dans le cadre du développement d'ARGOS Intelligence, une solution d'intelligence artificielle destinée à améliorer la traçabilité, l'analyse des risques et la prévision des événements de transport en Afrique centrale, je souhaite étudier les possibilités d'accès à vos données historiques opérationnelles.

Je recherche, dans la mesure où elles sont disponibles et communicables, les catégories de données suivantes :

1. Historiques d'arrivées et de départs, avec distinction entre heures prévisionnelles et heures effectivement observées.
2. Journaux de mouvements et d'escales des navires, véhicules ou marchandises.
3. Données de trajectoires horodatées et informations de suivi des expéditions.
4. Registres d'incidents, rapports d'enquête et niveaux de confirmation des événements.
5. Données relatives aux temps d'attente, aux passages de frontières et aux transferts entre opérateurs.
6. Métadonnées décrivant les champs, les unités, les règles de validation et les périodes couvertes.

Pour chaque catégorie, je souhaiterais connaître la période disponible, la fréquence des observations, le format d'export, les conditions d'accès, les restrictions de réutilisation et les éventuels coûts.

Un premier échantillon anonymisé, accompagné de son dictionnaire de données, serait particulièrement utile pour évaluer la qualité des observations et définir un protocole de validation scientifique.

Les données seraient utilisées dans le respect des autorisations accordées, des exigences de confidentialité et des règles de gouvernance convenues avec votre organisme. Aucune donnée ne serait présentée comme confirmée sans une source et un niveau de vérification appropriés.

Je vous remercie de bien vouloir m'indiquer le service compétent pour examiner cette demande ainsi que les formalités nécessaires.

Cordialement,

Équipe projet ARGOS Intelligence

## 13. État réel de l'inventaire

| Catégorie                                                  | État après les recherches effectuées                                            |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Statistiques portuaires du Cameroun                        | Disponibles publiquement sous forme agrégée et exportable pour certaines séries |
| Heures d'escales à Pointe-Noire                            | Des dates et heures sont publiées ; validation ligne par ligne nécessaire       |
| Horaires de navires vers Matadi                            | Disponibles pour certaines dates, mais principalement prévisionnels             |
| Incidents maritimes régionaux                              | Registre public du CRESMAC et rapports d'enquête accessibles via GISIS          |
| Trajectoires AIS historiques complètes                     | Accès à négocier ou à vérifier selon le fournisseur et le corridor              |
| Heures réelles d'arrivée reliées aux trajets               | Extraction opérationnelle à obtenir                                             |
| Historique complet des transferts routiers et ferroviaires | Aucun jeu régional complet vérifié dans cette recherche                         |
| Gouvernance et droits de réutilisation                     | À établir avec chaque détenteur des données                                     |

Conclusion : les ressources réelles identifiées permettent de démarrer la collecte et de construire un registre documentaire régional. Elles ne permettent pas encore d'affirmer que nous disposons d'un jeu complet et propre à l'entraînement d'ARGOS. La priorité est d'obtenir les données opérationnelles brutes, avec leurs horodatages, leurs identifiants, leurs preuves et leurs droits d'utilisation, puis de mesurer leur qualité avant de choisir la taille et l'architecture définitives des modèles.
