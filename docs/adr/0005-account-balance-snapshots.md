# ADR 0005: Dated account balance and valuation snapshots

- Status: Accepted
- Date: 2026-08-28
- Product baseline: Product Specification v1.0

## Context

Opening balances are starting points, not mutable representations of a current
account value. Transactions preserve economic events, while investment and
other value-based accounts also need periodic market values that cannot be
derived from cash movements alone.

## Decision

- A dated `AccountSnapshot` preserves each reported balance or valuation as a
  separate Ledger record. Updating the account opening balance is not used for
  later reconciliation.
- One snapshot is allowed per account and valuation date. Corrections update
  that identifiable observation; archive and restore preserve its lifecycle.
- The account currency, base currency, converted balance, historical FX rate,
  and FX status are frozen on the snapshot. Missing foreign-currency FX remains
  visible instead of inventing a conversion.
- Calculated account balance uses the opening balance plus active Ledger events
  whose posting date is on or before the snapshot date. Expenses and outgoing
  transfer legs reduce it; income, refunds, reimbursements, and incoming
  transfer legs increase it.
- A transaction in another currency uses its frozen converted amount when that
  amount is in the account currency. If no account-currency value is available,
  the calculation is explicitly incomplete and no difference is reported.
- Investment and value-based accounts present snapshots as valuations. The UI
  does not label the difference from cash-ledger balance as income or return.
  Performance attribution remains a later analytical slice.
- Production and Demo/Test store snapshots in their separate PostgreSQL data
  planes. Demo/Test reset truncates its snapshots, and the isolation scenario
  proves that Production snapshots survive unchanged.

## Consequences

Users can record monthly investment values and reconcile ordinary accounts
without rewriting history. Explicit balance-adjustment events, investment
trades, realized/unrealized performance, and full CR-021 reconciliation remain
separate future work.
