#!/bin/sh
local_port=${ARTHENA_PORT:-5006}
public_url=$(docker compose logs cloudflared 2>/dev/null \
  | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' \
  | tail -n 1 || true)

printf 'Adresse locale : http://localhost:%s\n' "$local_port"
if [ -n "$public_url" ]; then
  printf 'Adresse publique : %s\n' "$public_url"
else
  printf 'Adresse publique indisponible. Consultez : docker compose logs cloudflared\n'
fi
