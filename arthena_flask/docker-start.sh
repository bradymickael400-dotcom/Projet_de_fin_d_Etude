#!/bin/sh
set -eu

docker compose up -d --build

printf '\nArthena démarre. Attente de l URL Cloudflare'
attempt=0
public_url=""
while [ "$attempt" -lt 45 ]; do
  public_url=$(docker compose logs cloudflared 2>/dev/null \
    | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' \
    | tail -n 1 || true)
  if [ -n "$public_url" ]; then
    break
  fi
  printf '.'
  sleep 2
  attempt=$((attempt + 1))
done

local_port=${ARTHENA_PORT:-5006}
printf '\n\nAdresse locale : http://localhost:%s\n' "$local_port"
if [ -n "$public_url" ]; then
  printf 'Adresse publique : %s\n' "$public_url"
else
  printf 'Tunnel pas encore prêt. Relancez : ./docker-urls.sh\n'
fi
printf '\nComptes de démonstration (mot de passe : demo123) :\n'
printf '  Parent       parent@demo.cm\n'
printf '  Enseignant   prof@demo.cm\n'
printf '  Admin école  admin@demo.cm\n'
printf '  Super admin  super@demo.cm\n'
