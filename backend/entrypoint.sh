#!/bin/bash
set -e

echo "Waiting for database to be ready..."
while ! pg_isready -h postgres -U ${POSTGRES_USER:-marketer_user} -d ${POSTGRES_DB:-marketer_db} > /dev/null 2>&1; do
    sleep 1
done

echo "Running database migrations..."
python -m alembic upgrade head

echo "Starting application..."
exec "$@"
