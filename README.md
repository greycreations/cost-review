# Cost Review
<img width="1218" height="1125" alt="image" src="https://github.com/user-attachments/assets/3295c3cf-31a2-461f-b592-c4aaaebc1eea" />

Cost Review is a private, self-hosted web application for trustworthy personal
and household economics. Product behavior is defined by
`docs/PRODUCT_SPECIFICATION.md` v1.0 and delivered in the order described by
`docs/IMPLEMENTATION_BACKLOG.md`.

Sprint 1 established the Platform Foundation: PostgreSQL, migrations, first-run
setup, local authentication, independent locale settings, reverse-proxy safety,
and a persistent hard boundary between Production and Demo/Test. The current
pilot slice adds accounts, reusable ledger master data, manual income and
expense entry, historical FX persistence, real period summaries, and dated
account balance/value snapshots. Refunds and reimbursements are now preserved
as linked events that reduce net cost without weakening that boundary or being
misclassified as income. Transactions can be split across categories, tags,
base-cost classifications, and sharing parties. The full event is preserved
while Overview can switch between Total and My Share, including proportional
refunds and reimbursements. The same perspective controls budget outcome,
trends, and underlying entries. Overview applies the same filters to totals,
charts, comparison periods, and transaction drill-down. It also adds
explicit reconciliation adjustments, an audit-backed Recycle Bin, and encrypted
database/configuration/attachment backups with offline restore.

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

### Install a published release on Ubuntu

Release installations need only two files; source code and local build tools
are not required. Download `compose.yaml` and `cost-review.env.example` from
the selected GitHub release after its container images have been published,
then run:

```sh
mkdir -p cost-review && cd cost-review
mv /path/to/downloaded/compose.yaml ./compose.yaml
mv /path/to/downloaded/cost-review.env.example ./.env
nano .env
docker compose pull
docker compose up --detach --wait
```

Set `COST_REVIEW_VERSION` to the release version and replace every placeholder
password/key before the first start. The deployment file starts the two API
instances, both isolated PostgreSQL databases, the gateway, and both scheduled
backup processes without a profile flag. Open `http://SERVER-IP:8080` unless
`GATEWAY_PORT` was changed.

Container packages inherit the repository visibility when first published. If
they are private, authenticate the Ubuntu host using a GitHub token with
`read:packages` before `docker compose pull`:

```sh
echo "$GHCR_TOKEN" | docker login ghcr.io -u GITHUB_USERNAME --password-stdin
```

Never copy a development machine's `.env` to another installation. Generate
new database passwords and backup keys for every installation.

### Build from source for development

Create local configuration from the example. Replace both database passwords
with different long random values and set two different backup encryption keys
of at least 32 characters. Store a recovery copy of those keys away from this
repository and away from the Docker host:

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

Enable scheduled encrypted backups after the keys have been configured:

```sh
docker compose --profile backup up --build --detach --wait
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

Each `.crbackup` includes the applicable PostgreSQL database (including
configuration), the data plane's attachments, a manifest, and checksums. The
archive is authenticated and encrypted using that data plane's installation
key. Manual copying of PostgreSQL volume files is not a supported backup method.

Manual backups can be created, validated, and downloaded under **Settings**.
Automatic retention is configured with `BACKUP_*_RETENTION_COUNT`; it never
removes manual or pre-restore safety backups. Keep at least one recently
validated download on a different machine or storage service.

### Offline restore drill

Restore one data plane at a time. The filename must belong to that environment.
For Production:

```sh
docker compose stop api-prod backup-prod
docker compose run --rm --no-deps api-prod \
  python -m app.backup_cli validate manual-production-YYYYMMDDTHHMMSSZ-ID.crbackup
docker compose run --rm --no-deps api-prod \
  python -m app.backup_cli restore manual-production-YYYYMMDDTHHMMSSZ-ID.crbackup \
  --confirmation "RESTORE PRODUCTION"
docker compose up --detach --wait api-prod
```

Use `api-test`, `backup-test`, a `test` filename, and confirmation
`RESTORE DEMO/TEST` for Demo/Test. Restore validates the complete encrypted
archive before overwrite, creates a new pre-restore safety backup, replaces the
database and attachments, and invalidates all restored sessions. Do not run a
restore while the corresponding API or scheduler is active.

## Reverse proxy and Cloudflare

- Only the frontend/gateway publishes a host port in the standard Compose file.
- API and database services remain internal to Docker networks.
- Nginx forwards the original host, client address, and scheme.
- The API trusts only the gateway's fixed edge-network address by default.
- Set the exact public host/origin and enable secure cookies for HTTPS.
- Preserve the environment prefixes `/api/production/` and `/api/test/` when an
  outer proxy forwards to the gateway.

For the documented home-network topology, Cloudflare Tunnel on `192.168.1.40`
should forward the public hostname to `http://192.168.1.41:8080`. The Ubuntu
host publishes only that gateway port; PostgreSQL and APIs remain private Docker
services. Set `COOKIE_SECURE=true` and configure the exact public hostname and
origin before exposing the application.

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

Version tags matching `vMAJOR.MINOR.PATCH` also publish provenance and
SBOM-enabled `linux/amd64` and `linux/arm64` API/frontend images to GitHub
Container Registry. Release deployments pin `COST_REVIEW_VERSION` rather than
silently following `latest`. The same workflow creates a GitHub release with
`compose.yaml`, `cost-review.env.example`, and checksums so an Ubuntu installation does
not require cloning or building the source repository. The environment asset
is named `cost-review.env.example` in the release because GitHub rewrites
leading-dot asset names.

The isolation scenario creates independent Production/Test users, accounts,
transactions, linked transfers, snapshots, and budgets, proves writes cannot
cross the boundary, resets Demo/Test, and proves Production identity, settings,
accounts, budgets, and economic events are unchanged. It also proves the Test API cannot resolve or
connect to the Production database network and that the reset route is absent
in Production.

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
| GET/POST | `/api/v1/accounts/{id}/snapshots` | Dated account balance or valuation history |
| PATCH/POST | `/api/v1/account-snapshots/{id}[...]` | Correct, archive, or restore a snapshot |
| POST | `/api/v1/account-snapshots/{id}/adjustment` | Create one explicit reconciliation adjustment |
| GET/POST/PATCH | `/api/v1/categories[...]` | Arbitrary-depth category hierarchy plus archive/restore |
| GET/POST/PATCH | `/api/v1/providers[...]` | Provider records and lifecycle |
| GET/POST/PATCH/DELETE | `/api/v1/providers/.../aliases`, `/api/v1/provider-aliases/...` | Canonical provider aliases |
| GET/POST/DELETE | `/api/v1/provider-links`, `/api/v1/category-links` | Non-destructive analytical relationships |
| GET/POST/PATCH | `/api/v1/tags[...]`, `/api/v1/sharing-parties[...]` | Reusable tags and sharing-party register |
| POST | `/api/v1/tags/{id}/merge` | Confirmed reference-safe tag merge with conflict detection |
| GET/POST/PATCH | `/api/v1/transactions[...]` | Manual income/expense CRUD, filtering and archive/restore |
| POST | `/api/v1/transactions/{id}/refunds`, `/api/v1/transactions/{id}/reimbursements` | Create a linked recovery while preserving the gross expense |
| POST | `/api/v1/recoveries/{id}/archive`, `/api/v1/recoveries/{id}/restore` | Archive or restore a linked recovery |
| GET | `/api/v1/transactions/summary` | Canonical income, expense and cash-flow totals with Total/My Share perspective |
| GET | `/api/v1/transactions/analysis` | Filtered daily/category analysis with optional previous-period or previous-year comparison |
| GET/POST/PATCH | `/api/v1/transfers[...]` | Atomic owned-account transfers, filtering and archive/restore |
| GET/POST/PATCH | `/api/v1/analysis-groups[...]` | Reusable category/tag selections plus archive/restore |
| GET/POST/PATCH | `/api/v1/budgets[...]` | Budget lifecycle, period, rollover and filter selection |
| GET | `/api/v1/budgets/{id}/outcome` | Decimal-safe target, actual, remaining, overlap and consumption for a date range |
| GET | `/api/v1/budgets/{id}/transactions` | Traceable matching Ledger events and allocated recoveries |
| GET | `/api/v1/budgets/{id}/trend` | Server-derived recent outcomes using the budget's own periods |
| GET | `/api/v1/recycle-bin` | List recoverable archived Ledger records |
| GET | `/api/v1/audit-events` | Paginated material Ledger change history |
| GET/POST | `/api/v1/backups` | List or create encrypted backups |
| POST/GET | `/api/v1/backups/{filename}/validate`, `/download` | Validate or download one archive |

Ledger list endpoints return `{ items, total, limit, offset }`, support bounded
pagination, and hide archived master records unless `include_archived=true` is
requested. Master records use explicit archive/restore operations and appear in
the central Recycle Bin. Audit records material creates, updates, archives,
restores, balance adjustments, allocation changes, and tag merges.
Dependency-aware permanent deletion and bulk-edit grouping remain later Ledger
slices. See `docs/adr/0002-ledger-master-data-invariants.md`,
`docs/adr/0009-pilot-data-safety-and-offline-restore.md`, and
`docs/adr/0010-transaction-sharing-perspectives.md`. Release packaging is
defined in `docs/adr/0011-published-container-release.md`.

Transactions store an immutable economic date separately from posting and
system timestamps. Original amount/currency and the converted base-currency
amount/rate are persisted together. A foreign-currency entry may be saved when
the historical rate is unknown, but it is marked as missing FX and excluded
from canonical period totals until resolved. An internal transfer links one
outgoing and one incoming ledger leg, preserves both account-currency amounts
and historical FX, and is always excluded from ordinary income, expense, and
net cash-flow totals. Credit-card payments use this transfer workflow. Refunds,
and reimbursements are separate inflow events linked to their original expense;
they preserve gross cost, reduce net expense in summaries and analysis, and are
never counted as ordinary income. A split transaction remains one economic and
account event while its decimal-safe component amounts carry category, tag,
base-cost, and memo classification. PostgreSQL deferred constraints require the
components to equal the header amount exactly. Each component may allocate
multiple sharing parties by percentage; PostgreSQL requires an explicit
allocation to total exactly 100 percent. A reconciliation adjustment is an explicit system-sourced event
linked to one balance observation; it changes calculated balance but is excluded
from ordinary income/expense and budget analysis.

The Overview defaults to the current calendar month and supports explicit month
navigation. It visualizes daily income/expense movement and expenses by category,
with accessible tables containing the exact server-aggregated values. Account,
provider, category, tag, and base-cost filters use the same backend selection
semantics for totals and charts. Previous-period and previous-year comparisons
remain visually secondary to current values, and category bars drill down to the
contributing filtered transactions. Analysis Groups can now preserve reusable
category, tag, account, and provider include/exclude selections for budgets.
Saved views, recurring and amount/currency filtering in Overview, linked-master
rollups, and named/moveable dashboard layouts remain later Epic 5 slices.

The Budget view creates calendar-month, salary-cycle, calendar-year, or custom
budgets with reset/rollover behavior and category/tag/account/provider selection. Outcomes are
calculated by the API from canonical split components; linked refunds and
reimbursements reduce the relevant budget proportionally. Overlapping active
budgets are explicitly marked non-additive and every result can be drilled down
to its contributing Ledger events. A six-period trend uses each budget's own
period definition rather than inventing monthly periodization. Total/My Share
switches the actual, trend, and drill-down using the original split allocation;
the configured budget target remains explicit and unchanged. Actual/Periodized
views remain gated on the corresponding periodization semantics.

The Accounts view accepts dated reconciled balances and current values without
changing the opening balance or transaction history. Ordinary accounts compare
the observation with a posting-date-based calculated Ledger balance. Investment
and value-based accounts show valuation history without treating market-value
movement as income or claiming investment-performance attribution.

## Source of truth

1. `docs/PRODUCT_SPECIFICATION.md` — authoritative requirements baseline.
2. `docs/IMPLEMENTATION_BACKLOG.md` — delivery order and exit gates.
3. `docs/DESIGN.md` — approved visual and interaction language.
4. `docs/MVP.md` — compact technical delivery baseline.
5. `AGENTS.md` — contributor guardrails.

Material architecture decisions live under `docs/adr`.
