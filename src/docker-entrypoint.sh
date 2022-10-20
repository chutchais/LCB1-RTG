#!/bin/sh

echo "Start migrations..."

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput

exec "$@"