# ADR 0007: Budget selection and outcome semantics

- Status: Accepted
- Date: 2026-08-29
- Product baseline: Product Specification v1.0

## Context

Budgets must be flexible enough to select economic activity without introducing
a second, contradictory definition of cost. A budget may reuse an Analysis
Group, include or exclude classifications, overlap another budget, reset at a
period boundary, or carry its remaining amount forward. Every displayed outcome
must remain traceable to canonical Ledger events.

## Decision

- A budget stores a positive decimal amount in the installation base currency,
  its effective dates, period type, and reset or rollover behavior. Money is
  persisted as PostgreSQL `NUMERIC`; canonical calculations use `Decimal`.
- Calendar month, salary-to-salary, calendar year, and custom intervals are
  explicit period types. Salary cycles use a stable day from 1 through 28.
  Custom intervals have an end date and cannot roll over.
- Analysis Groups and budgets have independent include/exclude selections.
  Their effective category and tag selections are combined. Within one
  dimension, include means any selected value; category and tag dimensions
  must match on the same transaction split; exclusion always wins.
- Category selections may include all descendants. The descendants are resolved
  against the current non-destructive category hierarchy at query time.
- Budget actuals reuse split classifications. Linked refunds and reimbursements
  are negative actuals allocated proportionally across the original expense's
  persisted splits. Gross history remains unchanged.
- Rollover is computed from complete prior budget periods, beginning at the
  budget's effective date. Activity before that date never enters the carry.
- Overlapping active budgets are allowed. The API returns potentially
  overlapping budget identifiers and the interface explicitly states that their
  totals are not additive.
- Outcome and drill-down are server-derived from the same compiled selection.
  The frontend does not recompute financial totals.
- Budgets and Analysis Groups live inside one data plane. Demo/Test reset removes
  only its own planning data; the separate Production database and API remain
  unreachable.

## Deliberate first-slice boundary

The reusable selection model currently covers categories, descendants, and
tags. Providers and accounts will join the same model in the next common-filter
slice. Total/My Share and Actual/Periodized choices are not shown until Ledger
sharing allocations and recurring-cost periodization exist; inventing those
values in the budget layer would violate the product's economic semantics.

## Consequences

Budget consumption is explainable, reversible through ordinary event lifecycle
operations, and consistent with Overview analysis. Later filters and
perspectives can extend the selection compiler without migrating or rewriting
the underlying transactions.
