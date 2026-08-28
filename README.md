# Cost Review

Cost Review is a private, self-hosted web application for trustworthy personal
and household economics. Product behavior is defined by
`docs/PRODUCT_SPECIFICATION.md` v1.0 and delivered in the order described by
`docs/IMPLEMENTATION_BACKLOG.md`.

Sprint 1 established the Platform Foundation: PostgreSQL, migrations, first-run
setup, local authentication, independent locale settings, reverse-proxy safety,
and a persistent hard boundary between Production and Demo/Test. The current
Sprint 2 slice adds accounts and reusable ledger master data without weakening
that boundary.

## Architecture

The same immutable frontend and backend images serve two separate data planes:

```text
Browser -> frontend/gateway :8080
           |-> /api/production/v1 -> api-prod -> db-prod
           `-> /api/test/v1       -> api-test -> db-test
```

`api-prod` and `api-test` have different PostgreSQL credentials, session/CSRF
cookie names, private data networks, attachment volumes, backup volumes, and
database volumes. Each database stores a generated data-plane identity and its
environment kind. An API refuses to start if a volume is mounted under the
wrong environment.

The Test API has no network attachment or credential for the Production
database. It alone exposes the strongly confirmed Demo/Test reset route. See
`docs/adr/0001-production-test-data-boundary.md`.

## Run with Docker Compose

Requirements:

- Docker Engine or Docker Desktop with Docker Compose v2.
- An Ubuntu host for the intended self-hosted deployment.

Create local configuration from the example and replace both database
passwords with different long random values:

```powershell
Copy-Item .env.example .env
```

On Linux/macOS:

```sh
cp .env.example .env
```

For local HTTP, `COOKIE_SECURE=false` is expected. Behind HTTPS or Cloudflare,
set it to `true` before creating sessions. Configure the exact public origin and
host in `APP_ALLOWED_ORIGINS` and `APP_ALLOWED_HOSTS`.

Build and start the complete stack:

```sh
docker compose up --build --detach --wait
```

Open <http://localhost:8080>. Production and Demo/Test are initialized
independently: select an environment, complete its first-run setup, then switch
and repeat for the other data plane. This creates independent password hashes,
settings, and session stores; it does not copy economic data.

Stop containers without deleting persistent volumes:

```sh
docker compose down
```

Do not add `--volumes` unless permanent deletion of both data planes and all
associated attachment/backup volumes is explicitly intended.

## Persistent storage

Compose creates six named volumes:

- `prod-db-data` and `test-db-data`;
- `prod-attachments` and `test-attachments`;
- `prod-backups` and `test-backups`.

Attachments and encrypted backup workflows are delivered later, but their
storage boundary exists from Sprint 1. A future backup is complete only when it
includes the applicable database, configuration, and attachment volume. Manual
copying of PostgreSQL volume files is not a supported backup method.

## Reverse proxy and Cloudflare

- Only the frontend/gateway publishes a host port in the standard Compose file.
- API and database services remain internal to Docker networks.
- Nginx forwards the original host, client address, and scheme.
- The API trusts only the gateway's fixed edge-network address by default.
- Set the exact public host/origin and enable secure cookies for HTTPS.
- Preserve the environment prefixes `/api/production/` and `/api/test/` when an
  outer proxy forwards to the gateway.

If the edge subnet or proxy topology changes, update
`APP_TRUSTED_PROXY_IPS`/the Compose network deliberately; do not broadly trust
arbitrary forwarded headers.

## Backend development

Use Python 3.12 or newer and a reachable PostgreSQL database. SQLite is not a
supported development or test substitute.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
`APP_ENVIRONMENT`, the environment-specific cookie names, allowed hosts/origins,
and writable attachment/backup roots. Then run:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Backend checks:

```powershell
ruff check .
alembic upgrade head
alembic check
pytest
```

The test suite requires PostgreSQL and refuses to run unless
`APP_ENVIRONMENT=test`.

## Frontend development

Use Node.js 22 or newer. The Vite development server proxies environment API
paths through the running gateway on port 8080.

```sh
cd frontend
npm ci
npm run dev
```

Frontend checks:

```sh
npm run lint
npm test
npm run build
```

## Migrations

The API containers run `alembic upgrade head` before serving requests. The same
migration history is applied independently to Production and Demo/Test.

For every schema change:

1. update SQLAlchemy models;
2. generate a descriptively named migration against PostgreSQL;
3. inspect all operations and constraint names;
4. upgrade an empty and an existing compatible PostgreSQL database;
5. run `alembic check`;
6. verify both data planes and isolation tests.

Never edit a migration that has been shared or applied outside the current
branch.

## Verification and CI

GitHub Actions runs three gates:

- backend lint, real PostgreSQL migration, drift check, and API tests;
- frontend lint, component tests, and production build;
- complete Compose startup plus an HTTP isolation scenario.

The isolation scenario creates independent Production/Test users and accounts,
proves ordinary Ledger writes cannot cross the boundary, resets Demo/Test, and
proves Production identity, settings, and accounts are unchanged. It also proves
the Test API cannot resolve or connect to the Production database network and
that the reset route is absent in Production.

## Current API

Each backend exposes `/api/v1`; the gateway adds `/api/production` or
`/api/test` before that path.

| Method | Backend path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Database and data-plane health |
| GET | `/api/v1/environment` | Persistent environment identity |
| GET | `/api/v1/setup/status` | First-run state |
| POST | `/api/v1/setup` | Atomic initial-user setup |
| POST | `/api/v1/auth/login` | Create opaque server-side session |
| GET | `/api/v1/auth/session` | Read current authenticated session |
| POST | `/api/v1/auth/logout` | CSRF-protected logout |
| GET/PATCH | `/api/v1/settings` | Independent locale/currency/timezone settings |
| POST | `/api/v1/test/reset` | Test-only strongly confirmed reset |
| GET/POST/PATCH | `/api/v1/accounts[...]` | Account list/create/read/update plus archive/restore |
| GET/POST/PATCH | `/api/v1/categories[...]` | Arbitrary-depth category hierarchy plus archive/restore |
| GET/POST/PATCH | `/api/v1/providers[...]` | Provider records and lifecycle |
| GET/POST/PATCH/DELETE | `/api/v1/providers/.../aliases`, `/api/v1/provider-aliases/...` | Canonical provider aliases |
| GET/POST/DELETE | `/api/v1/provider-links`, `/api/v1/category-links` | Non-destructive analytical relationships |
| GET/POST/PATCH | `/api/v1/tags[...]`, `/api/v1/sharing-parties[...]` | Reusable tags and sharing-party register |

Ledger list endpoints return `{ items, total, limit, offset }`, support bounded
pagination, and hide archived master records unless `include_archived=true` is
requested. Master records use explicit archive/restore operations; permanent
deletion, Recycle Bin, audit, tag merge, and percentage allocations remain in
their later Ledger slices. See `docs/adr/0002-ledger-master-data-invariants.md`.

## Source of truth

1. `docs/PRODUCT_SPECIFICATION.md` — authoritative requirements baseline.
2. `docs/IMPLEMENTATION_BACKLOG.md` — delivery order and exit gates.
3. `docs/DESIGN.md` — approved visual and interaction language.
4. `docs/MVP.md` — compact technical delivery baseline.
5. `AGENTS.md` — contributor guardrails.

Material architecture decisions live under `docs/adr`.
