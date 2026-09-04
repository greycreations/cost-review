# ADR 0006: Split transactions and shared analysis semantics

- Status: Accepted
- Date: 2026-08-29
- Product baseline: Product Specification v1.0

## Context

Analysis must remain traceable to canonical Ledger events. A purchase may need
several classifications without becoming several account movements, and every
Overview number must use the same selection semantics as the transaction list
opened from it. Refunds and reimbursements must continue to reduce the original
cost rather than become income when either side is split or filtered.

## Decision

- One transaction header remains one economic and account event. Two or more
  component rows make it a split transaction and carry category, tags,
  base-cost status, and an optional memo independently.
- Split input uses decimal values. Existing PostgreSQL deferred constraints
  remain the final invariant: component originals and converted amounts must
  equal their transaction header totals exactly at commit time.
- Historical conversion is persisted once on the header. Component converted
  amounts use the persisted rate, with the final component receiving only the
  decimal-rounding remainder so totals stay exact.
- Linked refunds and reimbursements inherit the original expense's analytical
  classification. Their recovered amount is allocated proportionally across
  the original components for category analysis and filters.
- Date, account, provider, category, tag, and base-cost filters share one backend
  selection model across transaction list, period summary, and analysis. When
  several component filters are present, one component must satisfy them
  together; matches from different components cannot be combined accidentally.
- Comparison periods are derived by the backend. `previous_period` is the
  immediately preceding inclusive range of equal length; `previous_year`
  preserves month/day where possible and maps leap day to February 28.
- Overview drill-down sends the active period and filters to Transactions. It
  does not synthesize a separate client-side analytical result.

This decision supersedes ADR 0003's temporary single-component UI limitation;
its event, FX, PostgreSQL, and Production/Test boundary decisions remain in
force.

## User-interface consequence

Transaction entry has an optional split editor with an explicit remaining
amount and cannot submit until allocation is balanced. Overview exposes quiet
comparison lines and bars, percentage context on metrics, common filters, and
clickable category bars. Exact values remain available in accessible tables.

## Deliberate deferrals

- Sharing allocations and Total versus My Share analysis.
- Recurring, arbitrary amount/currency, saved-view, and Analysis Group filters.
- Expenses, Income, Budget, and Investments dashboard families.
- User-configurable widget layouts and named dashboard layouts.

## Consequences

The first advanced analysis slice is reproducible and drillable without
rewriting Ledger history. Later dashboards can reuse this selection language
instead of introducing endpoint-specific definitions of income and cost.
