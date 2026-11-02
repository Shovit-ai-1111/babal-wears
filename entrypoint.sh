#!/bin/sh
set -eu

if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
  if [ "${DEMO_MODE:-1}" = "1" ]; then
    export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
    echo "Demo session key generated. Set DJANGO_SECRET_KEY to preserve sessions across restarts."
  else
    echo "DJANGO_SECRET_KEY is required outside demo mode." >&2
    exit 1
  fi
fi
if [ "${DEMO_MODE:-1}" != "1" ] && [ -z "${POSTGRES_PASSWORD:-}" ]; then
  echo "POSTGRES_PASSWORD is required outside demo mode." >&2
  exit 1
fi
python manage.py wait_for_db
python manage.py migrate --noinput
python manage.py collectstatic --noinput
if [ "${SEED_DEMO:-1}" = "1" ]; then
  python manage.py seed_demo
fi
exec "$@"
