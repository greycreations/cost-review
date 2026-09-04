# ADR 0008: Budget account/provider filters and period trends

- Status: Accepted
- Date: 2026-08-30
- Product baseline: Product Specification v1.0
- Extends: ADR 0007

## Context

Budget selection must cover accounts and providers as well as split-level
categories and tags. Recovery events create an ambiguity: a refund may arrive
in another account or carry another provider than the original purchase. Trend
analysis also risks silently periodizing annual or salary-cycle budgets when a
calendar-month dashboard is selected.

## Decision

- Budgets and Analysis Groups may include or exclude accounts and providers.
  Include choices are OR within each dimension; account, provider, category,
  and tag dimensions must all match; exclusion always wins.
- Account and provider filters apply to the original expense. A linked refund or
  reimbursement therefore reduces the same analytical budget even when the
  recovery event uses another receiving account or provider.
- Category and tag conditions still match one persisted split together. Header
  conditions cannot make classifications from separate splits match.
- Potential budget overlap now requires compatible account and provider scopes
  in addition to compatible category and tag scopes.
- The API derives recent trend points from the budget's own period definition.
  A calendar-month budget yields months, a salary budget yields salary cycles,
  and an annual budget yields years. A one-off custom budget yields one point.
- Each trend point reuses the canonical outcome service, including rollover,
  recoveries, effective dates, Decimal arithmetic, and missing-FX warnings.
  The frontend only visualizes returned values.
- Account/provider selection rows are stored inside the same isolated data plane
  as their budget. Demo/Test reset truncates these associations and cannot reach
  Production credentials, networks, or volumes.

## Consequences

Users can now define budgets such as “groceries on the household card from these
providers” without changing Ledger history. Trends remain economically honest
for all supported budget periods and can later feed a larger Budget dashboard.

Provider/category relationship expansion and arbitrary saved-filter reuse remain
part of the broader common-filter engine. Total/My Share and Actual/Periodized
still depend on their corresponding Ledger semantics.
