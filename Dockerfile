# syntax=docker/dockerfile:1

FROM python:3.10.4-slim-buster

WORKDIR /app

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

RUN pip3 install poetry \
  && poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

COPY alembic.ini /app/
COPY alembic/ /app/alembic/

COPY backend/ /app/backend/
COPY main.py /app/

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh

# Set the script as the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "main.py"]
