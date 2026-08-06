#!/bin/bash

set -e

echo "[INFO] Running migrations..."
python manage.py makemigrations
python manage.py migrate
echo "[INFO] Database migrations completed successfully."

exec "$@"
