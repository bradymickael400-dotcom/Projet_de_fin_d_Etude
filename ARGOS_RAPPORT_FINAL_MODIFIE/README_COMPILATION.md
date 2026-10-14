# Rapport ARGOS - compilation

Ce dossier contient uniquement les sources nécessaires au rapport, les figures
effectivement référencées et le PDF final.

## Compiler

Depuis ce dossier :

```bash
./compiler_rapport.sh
```

Le script supprime l'ancienne compilation, reconstruit toutes les références et
produit `main.pdf`. Il synchronise également
`ARGOS_RAPPORT_FINAL_MODIFIE.pdf` avec cette nouvelle version.

## Sources

- `main.tex` : document principal ;
- `preamble.tex` : mise en page A4, typographie et styles TikZ ;
- `00_*.tex` à `06_biblio.tex` : contenu du rapport ;
- `figures/` : illustrations utilisées par les chapitres.

Les diagrammes UML et les schémas matériels actualisés sont conservés en TikZ
dans `figures/*.tex`. Ils sont intégrés directement à la compilation : aucune
ancienne copie PDF, PNG ou SVG n'est nécessaire.

Le fichier `figures/ARGOS_diagrammes_UML.drawio` contient les versions
éditables diagrams.net du diagramme de classes et des deux diagrammes de cas
d'utilisation. Ses trois pages peuvent être modifiées ou exportées séparément.

## Prérequis

Une distribution TeX Live comprenant notamment `latexmk`, `tikz`, `pgfplots`,
`siunitx`, `tabularx`, `pdflscape`, `hyperref`, `cleveref` et `mdframed`.
