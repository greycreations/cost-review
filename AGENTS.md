# Cost Review contributor guide

This repository contains Cost Review, a private self-hosted application for understanding recurring and planned expenses. Read docs/MVP.md and docs/DESIGN.md before changing product behavior or the interface.

## Product guardrails

- Keep the product focused on cost intelligence, not general budgeting, banking, or bookkeeping.
- Preserve the user's entered amount and billing interval. Normalized monthly, quarterly, and annual values are derived views.
- Treat Expense as the financial commitment. A Provider is reusable master data and may be linked to many Expenses.
- Providers and Categories are first-class, editable entities. Never silently delete linked Expenses.
- Use decimal-safe arithmetic for money. Do not use binary floating point for canonical calculations.
- Store dates without assuming a browser timezone. Use UTC for timestamps and ISO 8601 at API boundaries.
- Keep advanced analytics out of Sprint 1, but avoid schemas or APIs that would make later analytical queries difficult.

## Required architecture

- Frontend: React, TypeScript, and Vite.
- Backend: Python, FastAPI, SQLAlchemy 2.x, and Alembic.
- Database: SQLite in development and the standard self-hosted deployment. Keep SQLAlchemy models portable enough for a future PostgreSQL migration.
- Deployment: Docker Compose with persistent data mounted at /app/data.
- API prefix: /api/v1.

## Repository conventions

- frontend contains the browser application.
- backend/app contains the FastAPI application and domain code.
- backend/alembic/versions contains immutable database migrations. Add a migration for every schema change; never edit a migration that may have been applied outside your branch.
- Tests should sit close to the boundary they verify: backend/tests for API and domain behavior, frontend/src for component tests.
- Keep API route functions thin. Put calculations and business rules in dedicated services.
- Use Pydantic request and response models at API boundaries; do not expose SQLAlchemy models directly.

## UI rules

- Follow the Nordic Financial Calm tokens and interaction rules in docs/DESIGN.md.
- Use semantic design tokens rather than hard-coded colors inside components.
- Do not use red to mean expensive; reserve destructive colors for destructive actions and errors.
- Prefer one clear primary metric and strong information hierarchy over grids of KPI cards.
- Ensure keyboard focus, labels, contrast, reduced-motion behavior, and responsive layouts are present from the start.

## Quality bar

Before completing a change, run the relevant formatters, linters, tests, production build, migration upgrade, and Docker Compose configuration check. Update README.md whenever setup or operating behavior changes.

Do not commit secrets, local databases, generated caches, build output, or environment-specific configuration.
