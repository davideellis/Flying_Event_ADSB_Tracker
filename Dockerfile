FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY migrations /app/migrations
COPY deploy /app/deploy
COPY alembic.ini /app/alembic.ini
COPY .env.example /app/.env.example

RUN pip install --no-cache-dir . \
    && chmod +x /app/deploy/start.sh

EXPOSE 8000

CMD ["/app/deploy/start.sh"]
