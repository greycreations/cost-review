FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir . \
    && addgroup --system costreview \
    && adduser --system --ingroup costreview costreview \
    && mkdir -p /app/storage/attachments /app/storage/backups \
    && chown -R costreview:costreview /app/storage

COPY alembic.ini ./
COPY alembic ./alembic

USER costreview

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
