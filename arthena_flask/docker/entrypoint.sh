#!/bin/sh
set -eu

secret_file=/app/instance/.secret_key
if [ -z "${SECRET_KEY:-}" ]; then
  if [ ! -s "$secret_file" ]; then
    python -c "import secrets; print(secrets.token_urlsafe(64))" > "$secret_file"
    chmod 600 "$secret_file"
  fi
  SECRET_KEY=$(cat "$secret_file")
  export SECRET_KEY
fi

flask --app wsgi.py db upgrade
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  flask --app wsgi.py seed-db
fi

exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  wsgi:app
