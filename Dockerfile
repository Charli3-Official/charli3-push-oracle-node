# syntax=docker/dockerfile:1

FROM python:3.10.18-slim-bookworm

WORKDIR /app

# Install git and SSH client
RUN apt-get update && apt-get install -y git openssh-client && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

# Setup SSH for private git repositories
RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

RUN pip3 install poetry \
  && poetry config virtualenvs.create false \
  && --mount=type=ssh poetry install --without dev --no-interaction --no-ansi --no-root

COPY alembic.ini /app/
COPY alembic/ /app/alembic/

COPY backend/ /app/backend/
COPY main.py /app/
COPY migrations.py /app/

CMD ["python3", "main.py"]
