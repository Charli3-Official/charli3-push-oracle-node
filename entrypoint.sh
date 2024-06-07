#!/bin/bash
# Stop on any error
set -e

# Run database migrations
echo "Running Alembic migrations"
alembic upgrade head

# Start the main application
echo "Starting the main application"
exec python3 main.py