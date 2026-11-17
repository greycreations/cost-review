FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# requirements.lock pins every runtime dependency with hashes
# (uv pip compile --universal --generate-hashes), so two builds of one tag
# install exactly the same third-party code.
COPY pyproject.toml requirements.lock ./
COPY app ./app
RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --require-hashes -r requirements.lock \
    && pip install --no-cache-dir --no-deps . \
    && addgroup --system costreview \
    && adduser --system --ingroup costreview costreview \
    && mkdir -p /app/storage/attachments /app/storage/backups \
    && chown -R costreview:costreview /app/storage

COPY alembic.ini ./
COPY alembic ./alembic

USER costreview

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
