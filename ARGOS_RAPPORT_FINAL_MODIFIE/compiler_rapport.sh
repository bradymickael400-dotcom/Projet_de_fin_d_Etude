#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[ARGOS] Nettoyage de l'ancienne compilation..."
latexmk -C main.tex >/dev/null 2>&1 || true
rm -f main.pdf main.synctex.gz

echo "[ARGOS] Compilation du rapport LaTeX..."
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

if [[ ! -s main.pdf ]]; then
    echo "[ARGOS] Erreur : main.pdf n'a pas été produit." >&2
    exit 1
fi

echo "[ARGOS] Synchronisation du document final..."
cp -f main.pdf ARGOS_RAPPORT_FINAL_MODIFIE.pdf

echo "[ARGOS] Suppression des fichiers temporaires..."
latexmk -c main.tex >/dev/null
rm -f main.synctex.gz

pages="$(pdfinfo main.pdf 2>/dev/null | awk '/^Pages:/ {print $2}')"
size="$(du -h main.pdf | awk '{print $1}')"

echo "[ARGOS] Compilation terminée."
echo "[ARGOS] Fichier : $SCRIPT_DIR/main.pdf"
echo "[ARGOS] Pages   : ${pages:-inconnu}"
echo "[ARGOS] Taille  : ${size:-inconnue}"
