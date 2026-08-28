# Cost Review — Release 1 Core MVP delivery baseline

**Status:** aligned with Product Specification v1.0

**Authoritative requirements:** `docs/PRODUCT_SPECIFICATION.md`

**Delivery order:** `docs/IMPLEMENTATION_BACKLOG.md`

This document is a compact technical delivery guide. It does not override the
Product Specification.

## Release 1 outcome

Cost Review is a self-hosted PostgreSQL-backed web application that preserves a
trustworthy economic ledger and supports controlled classification, recurring
events, safe import, analysis, budgeting, recovery, and a persistent isolated
Demo/Test environment.

The Release 1 Core MVP blockers are:

1. Platform foundation, setup, authentication, persistence, migrations, and a
   hard Production/Test boundary.
2. Accounts, balances, transactions, splits, income, expenses, transfers,
   refunds, reimbursements, adjustments, currency, and sharing.
3. Categories, providers and aliases/links, tags, and sharing parties.
4. Safe CRUD, audit, Recycle Bin, bulk edit, restore, and dependency-aware
   permanent deletion.
5. Versioned recurring definitions, Expected events, confirmation, and matching.
6. CSV/XLSX profiles, preview, staging, validation, duplicate handling, rules,
   import batches, and undo.
7. Common filters, saved views, Analysis Groups, predefined dashboards, and
   saved layouts.
8. Flexible budgets and Actual/Periodized plus Total/My Share perspectives.
9. Encrypted backup/restore with retention and an automated restore test.
10. Persistent Demo/Test with safe reset, import simulation, and selective
    one-way Production-to-Test configuration copy.

Attachments, manual investment/asset/debt views, goals, reporting/export, and
proactive alerts follow after the Core MVP is stable. The Product Specification
defines the complete extended and post-MVP boundaries.

## Platform baseline

- Docker Compose deployment on Ubuntu.
- React, TypeScript, and Vite frontend served through a same-origin gateway.
- FastAPI backend with a versioned `/api/v1` contract.
- SQLAlchemy 2.x and Alembic against PostgreSQL only.
- Local username/password authentication with secure hashing, opaque
  server-side sessions, CSRF protection, and secure cookie controls.
- First-run setup for initial login, language, region, date/number formats, base
  currency, week start, and timezone.
- Explicit reverse-proxy, trusted host/origin, and secure-cookie configuration.

## Production and Demo/Test boundary

Production and Demo/Test use the same application images but run as separate
data planes:

- separate API processes;
- separate PostgreSQL services and persistent volumes;
- separate database roles and passwords;
- separate Docker data networks;
- separate session and CSRF cookie namespaces;
- persistent environment identity stored in each database;
- startup refusal if a database volume is mounted under the wrong environment;
- Demo/Test-only destructive reset endpoint with strong confirmation;
- automated proof that reset and ordinary Test writes cannot mutate Production.

There is no shared `is_test` discriminator on economic rows. Future selective
configuration copy is an explicit API export/import operation and never grants
one data plane direct database access to the other.

## Sprint 1 — Platform Foundation

Sprint 1 implements backlog CR-001 through CR-008. It includes:

- reproducible Compose services for gateway, Production API/PostgreSQL, and
  Demo/Test API/PostgreSQL;
- persistent database, attachment, and backup volumes;
- initial platform migration;
- setup lock, authentication, sessions, settings, and environment identity;
- Swedish/English setup and shell foundations;
- unmistakable Production and Demo/Test UI states;
- trusted proxy/host/origin configuration;
- PostgreSQL-only tests, migrations, Compose smoke tests, and destructive
  isolation tests.

Sprint 1 intentionally does not create the old Expense-centric schema. The
ledger schema starts only after its transaction semantics and invariants have
been reviewed against Product Specification v1.0.

### Sprint 1 exit gate

- A fresh Compose deployment becomes healthy with documented steps.
- Both data planes migrate from empty PostgreSQL databases.
- Setup creates the first local user and then locks.
- Login, authenticated session lookup, logout, and settings retrieval work.
- Production and Demo/Test identities remain stable across container recreation.
- Both databases and storage volumes persist independently.
- Demo/Test reset is unavailable in Production and cannot alter Production.
- Cross-environment database credentials and network routes fail.
- The Demo/Test UI is persistent and unmistakable.
- Backend lint/tests, Alembic checks, frontend lint/tests/build, and Compose
  verification pass.

## Ledger sequence after Sprint 1

1. Accounts and hierarchical/reusable master data.
2. Transaction and TransactionSplit with original currency and historical FX.
3. Expense/income, transfer, refund, reimbursement, credit-card, and adjustment
   semantics.
4. Sharing, balances, reconciliation, soft deletion, Recycle Bin, audit, frozen
   historical identity, and bulk edit.

Recurring/Expected events remain a separate later epic and never replace actual
ledger events.
