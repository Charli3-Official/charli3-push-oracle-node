#!/bin/bash
# Stop on any error
set -e

# Run database migrations
echo "Running Alembic migrations"
alembic upgrade head
