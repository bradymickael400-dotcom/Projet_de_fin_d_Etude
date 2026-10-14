#!/usr/bin/env bash
set -euo pipefail

compose=(docker compose)
# Compose détectait Bake sans disposer du plugin buildx. Le constructeur Docker
# classique suffit pour ce projet et évite cet avertissement sans conséquence.
export COMPOSE_BAKE=false

echo "Démarrage d'ARGOS, de PostgreSQL, Redis, du worker et de Cloudflared..."
if ! getent hosts pypi.org >/dev/null 2>&1; then
    echo "ERREUR : pypi.org n'est pas résolu par l'ordinateur."
    echo "Vérifie la connexion Internet et le DNS, puis relance ce script."
    echo "Diagnostic conseillé : resolvectl status"
    exit 1
fi
"${compose[@]}" up -d --build db redis web worker

# Un Quick Tunnel peut expirer côté Cloudflare. Sa recréation garantit que les
# journaux contiennent uniquement l'URL du tunnel courant, jamais une ancienne.
"${compose[@]}" up -d --force-recreate cloudflared

echo "Attente de l'URL publique Cloudflare..."
public_url=""
for _ in $(seq 1 60); do
    public_url=$("${compose[@]}" logs --no-color cloudflared 2>&1 \
        | sed -nE 's#.*(https://[a-zA-Z0-9-]+\.trycloudflare\.com).*#\1#p' \
        | tail -n 1)
    if [ -n "$public_url" ]; then
        break
    fi
    sleep 2
done

echo
echo "ARGOS est lancé."
echo "URL locale  : http://localhost:5002"
if [ -n "$public_url" ]; then
    echo "Synchronisation de PUBLIC_BASE_URL pour les liens et QR codes..."
    if grep -q '^PUBLIC_BASE_URL=' .env; then
        sed -i "s#^PUBLIC_BASE_URL=.*#PUBLIC_BASE_URL=$public_url#" .env
    else
        printf '\nPUBLIC_BASE_URL=%s\n' "$public_url" >> .env
    fi
    "${compose[@]}" up -d --force-recreate web worker
    echo "URL publique: $public_url"
else
    echo "L'URL publique n'est pas encore disponible. Réessaie avec :"
    echo "docker compose logs cloudflared | grep -oE 'https://[^ ]+\.trycloudflare\.com'"
fi
echo
echo "État des services :"
"${compose[@]}" ps
