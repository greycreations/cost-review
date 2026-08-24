# Cost Review

Cost Review is a private, self-hosted application for understanding recurring and planned expenses. Sprint 1 establishes the technical foundation: a React and TypeScript interface, a FastAPI service, SQLAlchemy models, Alembic migrations, persistent SQLite storage, and a Docker Compose deployment.

The product and visual decisions live in docs/MVP.md and docs/DESIGN.md. AGENTS.md contains implementation guardrails for contributors.

## Current Sprint 1 scope

Implemented:

- Nordic Financial Calm application shell with honest empty states.
- Frontend-to-backend health and resource connectivity.
- Versioned API at /api/v1.
- SQLAlchemy entities for Provider, Category, and Expense.
- Read-only collection endpoints for the three initial entities.
- Initial Alembic migration with relational and domain constraints.
- Persistent SQLite data directory.
- Multi-stage frontend image, backend image, and Compose wiring.
- Backend API tests, frontend component tests, linting, and CI.

Intentionally deferred:

- Create, update, archive, reassign, and delete workflows.
- Searchable Provider and Category selectors.
- Expense forms and normalization calculations.
- Payments, amount history, advanced analysis, charts, imports, and exports.

## Run with Docker Compose

Requirements:

- Docker Engine or Docker Desktop with Docker Compose v2.

From the repository root:

    docker compose up --build -d

Open:

- Application: http://localhost:8080
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/api/v1/health

Stop the application:

    docker compose down

The SQLite database is stored at data/costreview.db on the host and mounted at /app/data/costreview.db in the backend container. Normal container recreation does not delete it. Do not use a volume-removal command when you intend to retain data.

## Local development

### Backend

Use Python 3.12 or newer.

    cd backend
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev]"
    New-Item -ItemType Directory -Force ..\data
    alembic upgrade head
    uvicorn app.main:app --reload

On macOS or Linux, activate the environment with:

    source .venv/bin/activate

The local default database path resolves to data/costreview.db at the repository root. Set DATABASE_URL when another location is preferred.

Backend checks:

    ruff check .
    pytest
    alembic check

### Frontend

Use Node.js 22 or newer.

    cd frontend
    npm install
    npm run dev

Vite serves the application at http://localhost:5173 and proxies /api requests to the backend at http://localhost:8000.

Frontend checks:

    npm run lint
    npm test
    npm run build

## Database migrations

The backend container runs alembic upgrade head before starting the API. For a local schema change:

1. Update the SQLAlchemy models.
2. Generate a migration with a descriptive name.
3. Inspect the generated operations and constraints.
4. Apply the migration locally.
5. Run tests and alembic check.

Never edit an already shared migration. Add a new migration instead.

## Backup and restore

For a consistent backup, stop writes and copy data/costreview.db to a safe location. Restore by stopping the application, replacing the database file with the backup, and starting the application so outstanding migrations can run.

The data directory is ignored by Git. Never commit a personal database.

## Project structure

    .
    ├── backend
    │   ├── alembic
    │   ├── app
    │   │   ├── models
    │   │   ├── api.py
    │   │   ├── database.py
    │   │   └── main.py
    │   └── tests
    ├── data
    ├── docs
    │   ├── DESIGN.md
    │   └── MVP.md
    ├── frontend
    │   └── src
    ├── AGENTS.md
    └── compose.yaml

## API foundation

Sprint 1 exposes:

| Method | Path | Purpose |
|---|---|---|
| GET | /api/v1/health | API and database connectivity |
| GET | /api/v1/providers | List Providers |
| GET | /api/v1/categories | List Categories |
| GET | /api/v1/expenses | List Expenses |

Mutation endpoints follow in the Provider and Category CRUD slice.
