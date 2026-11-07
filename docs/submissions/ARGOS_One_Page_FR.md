# ARGOS — suivi de conteneurs et examen des événements

**Équipe ARGOS · Présentation du projet · AI for Good Sandbox Hackathon**

## Pourquoi ARGOS

Pendant un transport, la position du conteneur, les mesures de ses capteurs et les informations des différents intervenants arrivent souvent séparément. ARGOS les rassemble pour que l’équipe chargée de l’expédition puisse voir ce qui s’est passé et vérifier une alerte avec son contexte.

## Ce que fait l’application

Le boîtier ESP32 transmet des positions GPS et les mesures disponibles, comme la température, les chocs ou l’ouverture de porte. L’API vérifie les messages et les associe à la boîte concernée. Des règles configurées déclenchent les alertes. La notification reste courte; la fiche du conteneur présente la mesure, l’heure, la position et le déclencheur.

Pour un trajet actif, ARGOS estime l’heure d’arrivée à partir de la distance restante sur l’itinéraire et des vitesses GPS récentes. C’est un calcul indicatif : il ne tient pas compte du trafic, des arrêts futurs ou des délais aux frontières et aux terminaux.

## La démonstration : un trajet, six étapes

Le scénario, entièrement simulé, suit un fret pharmaceutique de Douala à un yard intérieur. Il présente la déclaration et le scellé, la sortie du terminal, une alerte de porte et de température avec un GPS imprécis, une demande de partage de localisation, une lecture tardive au yard et une inspection proposée. Au moment du partage, le scénario s’arrête à une revue humaine : les informations fournies ne suffisent pas à valider la demande.

| Rôle simulé | Ce qu’il voit et examine |
|---|---|
| Opérateur | Mesures, position, trajet et vérifications du transport. |
| Douane-port | Déclaration, scellé et informations qui lui sont transmises. |
| Données et cybersécurité | Données concernées et demande de partage. |
| Conseiller neutre | Sources disponibles et points qui restent incertains. |

Le coordinateur distribue les faits par étape. Les rôles ne représentent aucune administration. Une personne reste responsable de toute décision opérationnelle.

## Comment les agents sont encadrés

Chaque rôle recherche dans sa propre partition documentaire. Les agents citent les passages retrouvés; si le corpus ne répond pas, ils signalent le manque d’information. La trace conserve les faits, les sources, les incertitudes et l’état de la revue humaine. Le rejeu fonctionne sans fournisseur externe; Gemini est facultatif.

Le corpus comprend des extraits sélectionnés de la loi camerounaise n° 2024/017, transcrits et contrôlés visuellement depuis le scan officiel, et un résumé limité de l’Accord de l’OMC sur la facilitation des échanges. Ces documents ne constituent pas une analyse juridique complète. Les références à ITU‑T Y.3172 et au cadre AI Ready servent à décrire l’architecture; ARGOS ne revendique ni certification ni score de préparation.

## Technologie et état actuel

Le prototype utilise Python et Flask, PostgreSQL/TimescaleDB, Redis, Leaflet, un boîtier ESP32 et une recherche documentaire locale par mots-clés. Le classifieur logistique entraîné sur des scénarios synthétiques est expérimental et ne produit pas les alertes de l’application. Le contrôle documentaire local a satisfait 12 requêtes de présence ou d’absence de sources attendues; ce résultat ne mesure pas l’exactitude juridique.
