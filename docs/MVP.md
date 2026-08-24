# Cost Review — Technical MVP Specification

Status: approved product baseline for implementation.

## 1. Product vision

Cost Review is a private, self-hosted web application for registering, understanding, and reviewing recurring and planned expenses. It answers one question exceptionally well:

> What are my financial commitments actually costing me?

It is a focused cost-intelligence tool, not a full budgeting, banking, investment, or accounting product. Users enter trustworthy source data once and can then normalize, filter, compare, aggregate, and visualize it without changing that source data.

The product principles are:

- clarity over complexity;
- transparency over hidden automation;
- control over convenience at any cost;
- insight over bookkeeping;
- capture once, analyze freely.

## 2. MVP outcomes

A user can:

1. Create, read, edit, duplicate, pause, reactivate, end, and permanently delete individual Expenses.
2. Create and reuse editable Providers and Categories through searchable selectors.
3. Store actual amounts and flexible recurrence intervals.
4. View equivalent recurring cost per month, quarter, or year without modifying stored data.
5. distinguish recurring commitments from one-time expenses and expected cost from actual Payments.
6. understand totals, category distribution, provider distribution, largest commitments, and upcoming payments.
7. explore data with filters, comparisons, tooltips, drill-down, and interactive charts.
8. review old, expensive, or soon-due commitments.
9. export data in CSV and JSON and back up the SQLite database.
10. install and run the application with Docker Compose while retaining data across restarts and upgrades.

## 3. Scope boundaries

### In scope

- Manual-first expense registration.
- Full CRUD for Expense, Provider, and Category.
- Reusable provider and category master data.
- Flexible recurrence and cost normalization.
- Exact and estimated amounts.
- Optional payment history and amount history.
- Overview, Expenses, Analysis, Upcoming, Review, and Settings views.
- Interactive analysis by category and provider.
- Single-user, self-hosted operation.
- Persistent SQLite storage, imports/exports, and backup guidance.

### Not in the MVP

- Bank connections or automatic transaction detection.
- Budgeting, net-worth, investment, tax, or accounting workflows.
- Multi-user accounts, permissions, or cloud synchronization.
- Automated cancellation or negotiation of subscriptions.
- Native mobile applications.
- Predictive or AI-generated financial advice.

## 4. Domain model

The complete MVP domain contains:

- Provider
- Category
- Expense
- Payment
- ExpenseAmountHistory
- ApplicationSettings

Sprint 1 establishes Provider, Category, and Expense. Later vertical slices add Payment, ExpenseAmountHistory, settings, complete CRUD behavior, normalization, and analysis.

Provider and Category each have a one-to-many relationship with Expense. Expense has one-to-many relationships with Payment and ExpenseAmountHistory.

### Provider

A Provider represents an organization or supplier such as Telia, Spotify, If, or Göteborg Energi. It is reusable master data, not a text label embedded in an Expense.

Fields:

- provider_id: immutable primary key.
- name: required display name.
- website: optional URL.
- notes: optional free text.
- status: active or archived.
- created_at and updated_at.

Names need not be database-unique, but the UI should warn about likely duplicates. Users can create, edit, archive, reactivate, and delete Providers. The Expense form searches existing Providers and offers an inline create action.

An unused Provider may be deleted. A referenced Provider may only be deleted after the user chooses to reassign affected Expenses, remove their Provider association, or cancel. Provider deletion must never delete Expenses.

### Category

Category is reusable master data used for organization and analysis.

Fields:

- category_id: immutable primary key.
- name: required display name.
- description: optional free text.
- status: active or archived.
- sort_order: integer ordering value.
- created_at and updated_at.

Users can create, rename, archive, reactivate, reorder, and delete unused Categories. Deleting a referenced Category requires reassignment; it never silently deletes Expenses.

Suggested initial categories are Housing, Utilities, Insurance, Transport, Telecom, Entertainment, Software & Services, Family, Health, Finance, Memberships, Shopping, and Other.

### Expense

Expense is the central financial commitment. Several Expenses may share one Provider; for example, Apple may provide iCloud+, Apple Music, and AppleCare as separate Expenses.

Fields:

- expense_id: immutable primary key.
- name: required, not unique.
- provider_id: optional foreign key.
- category_id: required foreign key.
- amount: required non-negative decimal.
- currency: ISO 4217 code, initially SEK.
- amount_type: exact or estimated.
- recurrence_unit: day, week, month, or year when recurring.
- recurrence_interval: positive integer when recurring.
- expense_type: recurring or one_time.
- start_date, end_date, and next_payment_date: optional dates.
- payment_method: optional invoice, direct_debit, credit_card, bank_transfer, or other.
- status: active, paused, or ended.
- notes: optional free text.
- created_at and updated_at.

Recurring Expenses require both recurrence fields. One-time Expenses have neither. End date cannot precede start date. Amounts use decimal-safe storage and calculation.

Permanent deletion requires explicit confirmation. When related history exists, the UI must state that controlled cascade deletion also removes it.

### Payment

A Payment is an actual financial event and remains separate from the expected Expense. Fields are payment_id, expense_id, payment_date, amount, currency, notes, created_at, and updated_at. Expense registration remains useful without payment history.

### ExpenseAmountHistory

Amount history prevents a legitimate price change from destroying historical analysis. Fields are history_id, expense_id, amount, valid_from, valid_to, and created_at.

When an existing amount changes, the user chooses between correcting the existing value and recording a new price from a selected date.

### ApplicationSettings

Initial settings are default_currency, locale, default_normalization_period, upcoming_horizon_days, and review_age_months. Defaults are SEK, sv-SE, monthly, 30 days, and 12 months.

## 5. Normalization model

Original values are immutable inputs to presentation. A dedicated backend service owns all canonical normalization.

Annualized recurring cost is calculated as follows:

- every N months: amount × 12 / N;
- every N years: amount / N;
- every N weeks: amount × 52 / N;
- every N days: amount × 365.2425 / N.

Monthly equivalent is annualized cost / 12, quarterly equivalent is annualized cost / 4, and annual equivalent is the annualized cost. One-time Expenses are excluded from recurring KPIs unless explicitly included.

The API should ultimately return both the normalized value and a human-readable calculation explanation. Estimated amounts remain visually identifiable throughout the UI and analysis.

Normalization period and analysis time range are separate concepts. For example, Last 12 months normalized as Monthly is valid.

## 6. Product views

### Overview

Shows one dominant recurring-cost total, its annual equivalent, active count, cost by category, largest commitments, upcoming actual payments, and review prompts. A global Monthly, Quarterly, Annual selector changes derived values only.

### Expenses

Provides searchable, sortable, filterable rows with original amount and recurrence alongside normalized cost. It supports add, edit, duplicate, pause/reactivate, end, and delete actions.

### Analysis

The product's primary differentiator. It supports category, provider, status, type, recurrence, time-range, and normalization filters; exact-value tooltips; clickable series; linked highlighting; drill-down to contributing Expenses; ranked costs; and comparison of selected categories or Providers.

### Upcoming

Shows actual expected payments by date for a configurable horizon. It does not substitute normalized values for cash events.

### Review

Surfaces commitments not reviewed within the configured age, expensive commitments, estimated values, annual payments due soon, and other user-controlled review signals.

### Settings

Manages Providers, Categories, defaults, export, and backup guidance.

## 7. API baseline

All endpoints live under /api/v1. Resource APIs use conventional list, read, create, partial update, and delete operations. Sprint 1 exposes a health endpoint and read-only collection endpoints for Provider, Category, and Expense to prove the full stack. Complete mutation semantics follow in the next vertical slice.

Errors use a consistent JSON shape with a stable code, readable message, and optional field details. List endpoints are designed for future pagination and filtering.

## 8. Deployment and data ownership

The standard installation command is docker compose up -d. SQLite lives at /app/data/costreview.db through a host-mounted ./data directory. Alembic migrations run before the API starts. Restarting or rebuilding containers must not remove data.

The repository must document backup, restore, and upgrade behavior. Secrets and personal financial data never enter source control. The architecture should not prevent a future move to PostgreSQL.

## 9. MVP quality attributes

- Trustworthy calculations and explicit destructive actions.
- Fast local interaction for a realistically sized personal dataset.
- Accessible keyboard navigation, focus, labels, contrast, and status messages.
- Responsive layouts for desktop, tablet, and mobile browsers.
- Clear loading, empty, error, and unavailable states.
- Automated tests for domain rules, API contracts, and critical UI behavior.
- Migrations and reproducible Docker builds.

## 10. Delivery sequence

### Sprint 1 — technical foundation

Create the React/TypeScript frontend, FastAPI backend, SQLAlchemy models for Provider, Category, and Expense, the first Alembic migration, persistent SQLite storage, Docker Compose deployment, API connectivity, and the initial Nordic Financial Calm application shell. Do not implement advanced analytics.

Acceptance criteria:

- Docker Compose starts the application.
- The frontend can reach the backend health and collection endpoints.
- The database and tables are created through Alembic.
- Data resides in the persistent ./data mount.
- Provider, Category, and Expense schemas exist with their core constraints.
- Relevant tests, builds, and configuration checks pass.
- README.md documents architecture, setup, commands, and current scope.

### Next vertical slices

1. Provider and Category CRUD with reusable searchable selectors and safe deletion handling.
2. Expense CRUD plus recurrence and normalization services.
3. Payment and amount-history flows.
4. First Analysis API and interactive Cost by Category experience.
5. Review, import/export, and backup refinements.
