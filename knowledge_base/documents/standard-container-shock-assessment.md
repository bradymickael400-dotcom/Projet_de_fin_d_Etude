# Conteneurs maritimes standards : interprétation des chocs par ARGOS

## Source de connaissance

Synthèse de l’étude technique utilisateur « seuils de résistance des conteneurs maritimes de 20 et 40 pieds » fournie le 29 octobre 2026, portant sur CSC 1972, ISO 668, ISO 1496-1 et ISO 1161. Cette synthèse conserve les réserves formulées dans cette étude. Les textes normatifs complets et la plaque CSC de chaque unité priment sur ce résumé.

## Valeurs structurelles à ne pas confondre avec un impact capteur

- Références dimensionnelles courantes : conteneur standard de 20 pieds, 6 058 × 2 438 × 2 591 mm; conteneur standard de 40 pieds, 12 192 × 2 438 × 2 591 mm. Les dimensions réelles, la masse brute admissible et la capacité de gerbage dépendent du marquage de l’unité.
- Gerbage : le cas de référence cité est une accélération de calcul de 1,8 g avec une masse d’empilement admissible inscrite sur la plaque CSC. Ce `g` décrit le cas de charge de gerbage et n’est pas un seuil d’impact à programmer dans un accéléromètre.
- L’étude cite aussi les charges d’essai de parois (0,4 Pg et 0,6 Pg), du toit rigide (300 kg sur une surface et une position prescrites), du plancher (essai de véhicule à 7 260 kg d’essieu selon la procédure), et une référence de rigidité transversale de 150 kN. Ce sont des sollicitations d’essai définies, pas des seuils de choc instantané.
- CSC/ISO n’établissent pas, dans cette étude, un seuil universel en G pour détecter un dommage après impact. La température, l’humidité, l’accélération et le choc doivent être interprétés selon l’unité, la cargaison, le montage et l’étalonnage des capteurs.

## Règles à appliquer par ARGOS

1. Un choc mesuré de 0 G ou sous le seuil opérationnel configuré ne constitue pas une alerte de dommage. Une valeur positive seule est une mesure, pas un incident.
2. ARGOS utilise le seuil `choc_max` propre à la boîte lorsque sa valeur est strictement positive. Une valeur absente, nulle, négative ou invalide est traitée avec le repli opérationnel ARGOS de 5 G, et doit être présentée comme tel. Ce repli n’est pas une valeur CSC/ISO.
3. Dépasser ce seuil est un signal de manutention à examiner. Un pic au moins deux fois supérieur au seuil déclenche la priorité d'inspection ARGOS; les dépassements répétés sont comptés séparément et recommandent un contrôle. Le niveau décrit une priorité de vérification, pas un dommage confirmé.
4. Le modèle ne doit jamais convertir une mesure en G en probabilité chiffrée de dommage structurel sur la base de cette étude. Retourner `damage_probability: null` ou l’équivalent et préciser que le capteur seul ne permet pas de diagnostiquer une déformation ou une fissure.
5. Pour évaluer un dommage, conserver le pic G, la durée si disponible, les axes/accélérogramme, le nombre d’impacts, l’heure, la position, la qualité et l’étalonnage du capteur, son emplacement, l’état de chargement et l’identifiant du conteneur. Recommander une inspection visuelle/technique après un impact significatif; la plaque CSC et le rapport d’inspection déterminent l’aptitude à poursuivre le transport.
6. Distinguer explicitement `mesure`, `seuil opérationnel ARGOS`, `niveau de vérification recommandé` et `dommage confirmé`. Ne jamais appeler le seuil ARGOS une limite réglementaire.

## Niveau de vérification opérationnel actuel

La règle ARGOS classe le pic inférieur au seuil comme « sous le seuil opérationnel »; un dépassement ponctuel comme « inspection recommandée »; un pic au moins deux fois supérieur au seuil comme « inspection prioritaire ». La répétition de dépassements est rapportée séparément. Ces catégories sont des règles de triage provisoires, sans calibration empirique ni valeur de probabilité. Les mesures axiales et de durée sont nécessaires pour une évaluation d’ingénierie plus précise.
