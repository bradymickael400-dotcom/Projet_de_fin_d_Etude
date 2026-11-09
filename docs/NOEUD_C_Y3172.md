# Nœud C — Collector (ITU-T Y.3172)

## Définition retenue

Dans le pipeline ML logique de Y.3172, **C signifie Collector** : il collecte les
données d’une ou plusieurs sources **SRC** et peut, selon le déploiement,
configurer ces sources pour contrôler la nature, la granularité ou la périodicité
des données produites. C est une fonction logique du pipeline, pas un protocole,
un lien Wi-Fi ou un équipement obligatoirement distinct.

## Réalisation dans ARGOS

| Fonction logique | Réalisation ARGOS | Preuve dans le dépôt |
|---|---|---|
| SRC | ESP32 et capteurs embarqués; le pont Wi-Fi direct est une autre interface d’entrée | `firmware/argos_esp32/`, `app/modules/iot/controller.py` |
| C — collecte | Fonction `collect_telemetry`, utilisée par les deux voies d’ingestion pour valider et accepter les messages SRC et enregistrer les trames validées | `app/modules/iot/collector.py`, `app/modules/iot/iot_service.py` |
| Interface de collecte | API `/api/iot/telemetry` authentifiée par clé appareil; API `/api/black-boxes/<id>/direct-telemetry` authentifiée par session et autorisation de boîte | `app/modules/iot/controller.py` |
| Sortie de C vers PP | Objet télémétrique normalisé par le contrat de validation et identifiant du message brut, remis aux fonctions de liaison, normalisation qualité et publication | `app/modules/iot/validator.py`, `app/modules/iot/iot_service.py` |
| Provenance et erreurs | Trames validées ou rejetées journalisées dans `iot_raw_messages`, avec état, adresse distante et raison de rejet | `app/modules/iot/repository.py`, `app/modules/iot/collector.py` |

La collecte vérifie le format de télémétrie, l’UUID de message, l’identité de la
source, le temps, la séquence, les coordonnées et les types/plages des champs
capteurs. Le service aval authentifie le terminal, vérifie son affectation à la
boîte/conteneur, puis transmet les données à la normalisation, au cache temps
réel, au stockage et aux évaluateurs d’alertes.

## Limites de conformité

Cette implémentation matérialise le rôle logique de collecte C pour ARGOS. Elle
ne suffit pas à déclarer l’application conforme à toute Y.3172 : ARGOS n’est pas
ici présenté comme un réseau IMT-2020, le collecteur ne configure pas encore les
paramètres d’acquisition des SRC, et le dépôt ne démontre pas à lui seul un
pipeline complet d’apprentissage automatique ni les fonctions de gestion et
d’orchestration ML décrites par la recommandation.

Référence : [ITU-T Y.3172 (fiche officielle)](https://www.itu.int/rec/T-REC-Y.3172/en)
et [texte intégral, clause 8.1](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-Y.3172-201906-I%21%21PDF-E&lang=e&type=items).
