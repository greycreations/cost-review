# Changelog

All notable changes per release. Dates are tag dates.

## 0.9.0 — Trust release (unreleased)

Security and data safety

- One household per data plane with roles: **owner**, **member** and **viewer**
  (ADR 0019). Viewers can read but not change the Ledger. Only owners manage
  members, backups and the Demo/Test reset. Administrators become owners and
  other accounts members on upgrade.
- Self-registration is disabled by default (`ALLOW_SELF_REGISTRATION=false`).
- Sign-in lockout after five consecutive failures (15 minutes), uniform cost for
  unknown usernames, and gateway rate limiting of sign-in, registration and setup.
- "My Share" is personal: a sharing party can be linked to a household member,
  and every member sees their own share. The former "represents me" party is
  linked to the oldest owner.
- Audit events record which member made a change.
- Backup format 2 encrypts in authenticated 1 MiB chunks, so creating,
  validating and restoring use constant memory (ADR 0020). Format 1 backups are
  still readable. Restore refuses backups from a newer release.

Household economics

- CSV/XLSX import with preview, suggested mapping, saved import profiles,
  staging, corrections, bulk approval and categorisation, duplicate detection,
  atomic commit and undo (ADR 0021).
- Recurring income and expenses with versioned amounts, Expected occurrences that
  never affect Actual figures, confirmation by recording or linking a
  transaction, deviation against a tolerance, and skip/reopen (ADR 0022).

Quality and operations

- Total/My Share rules in one shared module; one shared list of household tables
  for the Demo/Test reset and the test suite.
- Property-based tests (Hypothesis) for share allocation, recovery allocation,
  amount parsing and schedules.
- Python runtime dependencies locked with hashes (`backend/requirements.lock`);
  Dependabot for pip, npm, Docker, Compose and GitHub Actions; critical image
  vulnerabilities fail CI.
- The Demo/Test data plane is the Compose profile `demo-test`, enabled by
  `COMPOSE_PROFILES=demo-test` in `.env`.
- Frontend: the application shell, Settings and Transactions are split into
  smaller modules, and user-visible text lives in catalogs under
  `frontend/src/i18n`.
- Investments are unchanged in this release.

## 0.8.0 — 2026-09-12

- Device-persistent light/dark theme.
- Direct removal of a single holding next to bulk selection.
- Sortable columns in every Investments table.
- Ordinary-dividend comparison validated against Avanza: exact ticker, current
  payout and two comparable payout cycles before a share may rank.

## 0.7.0 — 2026-09-12

- Network self-registration, self-service password change and administrator
  user management (ADR 0015).
- Screener selection separated from durable holdings; expanded holdings table
  and dividend calendar; historical dividend-yield comparison.
- Searchable Swedish fund data from Avanza's public information, decimal fund
  units and a combined stock/fund purchase plan.
- Narrow-screen layout throughout the application.

## 0.6.0 — 2026-09-11

- Dynamically discovered Yahoo Finance universe of Stockholm-traded shares,
  persisted holdings, dividend estimates and whole-share purchase planning.

## 0.5.0 — 2026-09-11

- Server-side Stockholm market data with Yahoo Finance as the keyless default
  and EODHD as an alternative.

## 0.4.0 – 0.4.2 — 2026-09-05 to 2026-09-06

- Published container images and the two-file installation (ADR 0011).

## 0.3.0 – 0.3.2 — 2026-09-04

- Pilot data safety: reconciliation adjustments, audit-backed Recycle Bin,
  encrypted backups and offline restore (ADR 0009).
- Split transactions with sharing allocations and the Total/My Share
  perspective (ADR 0010).

## Before 0.3.0

- Platform foundation: PostgreSQL, migrations, first-run setup, local
  authentication, locale settings, reverse-proxy safety and the hard
  Production/Demo-Test boundary (ADR 0001).
- Accounts, master data, manual income and expense entry, historical FX,
  transfers, refunds and reimbursements, account snapshots, budgets and the
  Overview.
