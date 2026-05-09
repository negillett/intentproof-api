#!/usr/bin/env sh
set -eu
cd /app || exit 1
alembic upgrade head
exec "$@"
