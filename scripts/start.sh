#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py seed_content
python manage.py bootstrap_admin
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --threads 2 --timeout 60 --access-logfile - --error-logfile -
