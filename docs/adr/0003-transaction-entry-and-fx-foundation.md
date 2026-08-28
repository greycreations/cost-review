# ADR 0003: Transaction entry and FX foundation

- Status: Accepted
- Date: 2026-08-28
- Product baseline: Product Specification v1.0

## Context

The first economic Ledger slice must let a user record and review real entries
without flattening future transfers, refunds, reimbursements, adjustments, or
investments into ordinary income and expenses. Money and historical currency
conversion must remain trustworthy even before automated FX retrieval exists.

## Decision

- A transaction header preserves source, economic transaction date, posting
  date, description, original amount/currency, converted amount, base currency,
  and the historical FX rate/status actually used.
- Component rows carry category, tags, and base-cost semantics. Manual entry in
  this slice creates exactly one component, while the schema and PostgreSQL
  deferred balance triggers establish the future split boundary.
- PostgreSQL checks and commit-time triggers require positive decimal amounts
  and exact equality between header and component totals. Canonical money never
  uses binary floating point.
- Manual entry exposes only `expense` and `income`. Other event kinds are not
  simulated with those types; they remain unavailable until their linking and
  double-counting invariants are implemented.
- Same-currency entries persist a converted amount equal to the original amount
  and an FX rate of one. Foreign-currency entries persist either a complete
  conversion or an explicit `missing` FX state.
- Missing FX never blocks preservation of an original event. Such entries stay
  visible and are counted as requiring attention, but are excluded from
  canonical base-currency income, expense, and net totals.
- Archive and restore are explicit. Permanent deletion and the audit-backed
  Recycle Bin remain CR-022 and CR-023.
- Production and Demo/Test have the same transaction schema but store and serve
  every row through their already separate API, PostgreSQL, network, credential,
  session, and volume boundaries. Test reset includes transaction components and
  tags and cannot reach Production.

## User-interface consequence

The browser application has separate Overview, Transactions, Accounts, and
Settings views. Daily entry no longer shares a page with all master-data forms.
Provider and category can be created inline while entering a transaction;
full register maintenance remains in Settings. Overview and period summaries
show only persisted data and present an honest empty state when none exists.

## Deliberate deferrals

- Transfer pairs, refunds, reimbursements, investment events, balance
  adjustments, and opening balances keep their distinct Product Specification
  semantics and are not exposed by the transaction-entry API yet.
- Multi-component split editing, share allocation, automated FX retrieval,
  calculated balances/reconciliation, dependency-aware deletion, and full
  audit history remain their ordered Epic 2 backlog items.

## Consequences

The application is usable for manual income and expense capture plus a basic
real period review, while incomplete semantics cannot silently distort totals.
Later Ledger slices extend the event and component model instead of rewriting
the original transaction history.
