# Cost Review contributor guide

Cost Review is a private, self-hosted application for trustworthy personal and
household economics. Read `docs/PRODUCT_SPECIFICATION.md`,
`docs/IMPLEMENTATION_BACKLOG.md`, `docs/DESIGN.md`, and `docs/MVP.md` before
changing product behavior, architecture, or the interface.

`docs/PRODUCT_SPECIFICATION.md` v1.0 is the requirements baseline and takes
precedence when an older document conflicts with it.

## Product guardrails

- Preserve original economic events and source data. Analysis is derived and
  must not destructively rewrite history.
- Transactions, splits, transfers, refunds, reimbursements, investment events,
  debt reduction, balance adjustments, Expected events, and opening balances
  have distinct semantics.
- Use decimal-safe arithmetic for money. Never use binary floating point for
  canonical calculations.
- Preserve original currency, converted amount, and the historical FX rate
  actually used.
- Store timestamps in UTC and keep economic dates separate from timestamps.
- Put domain invariants in backend services and database constraints where
  appropriate. Keep API routes thin.
- Automation may suggest. Ambiguous or conflicting actions stay visible and
  require user confirmation.
- Production and Demo/Test are separate trust domains. Never represent that
  boundary solely with a row-level flag.

## Required architecture

- Frontend: React, TypeScript, and Vite.
- Backend: Python, FastAPI, SQLAlchemy 2.x, and Alembic.
- Database: PostgreSQL in development, CI, Demo/Test, and production. SQLite is
  not a supported runtime or test substitute.
- Deployment: Docker Compose on Ubuntu, suitable for a trusted reverse proxy or
  Cloudflare deployment.
- API: versioned under `/api/v1` inside each data plane. The gateway may add an
  environment routing prefix without changing the backend API contract.
- Production and Demo/Test run as separate API instances with separate
  PostgreSQL services, credentials, networks, session namespaces, and volumes.
- Database, attachment, and backup storage must be persistent and excluded from
  source control.

## Repository conventions

- `frontend` contains the browser application and gateway configuration.
- `backend/app` contains the FastAPI application, domain services, and models.
- `backend/alembic/versions` contains immutable migrations. Never edit a
  migration that may have been shared or applied outside the current branch.
- Use Pydantic request and response models at API boundaries; never expose
  SQLAlchemy models directly.
- Keep environment selection explicit in configuration and responses. A
  backend process must receive credentials for exactly one data plane.
- Tests must use PostgreSQL and must prove Production/Test isolation for every
  destructive Demo/Test operation.

## UI rules

- Follow the Nordic Financial Calm system in `docs/DESIGN.md`.
- Use semantic design tokens rather than hard-coded component colors.
- Never use red merely because a cost is high.
- Production and Demo/Test context must be unmistakable without relying on
  color alone.
- Provide Swedish and English foundations, visible labels, keyboard focus,
  WCAG AA contrast, reduced-motion behavior, and responsive layouts.
- Empty states must be honest and must not imply that fictional values are live
  financial data.

## Security and quality bar

- Never commit secrets, personal financial data, generated databases, caches,
  build output, or environment-specific configuration.
- Use secure password hashing, opaque server-side sessions, HttpOnly cookies,
  CSRF protection, explicit trusted hosts/origins/proxies, and environment-
  scoped cookie names.
- Before completing a change, run relevant formatting, linting, PostgreSQL
  integration tests, migration upgrade and drift checks, frontend tests/build,
  Compose validation, and isolation tests.
- Update README and architecture decisions whenever setup, deployment, trust
  boundaries, backup behavior, or operating requirements change.
