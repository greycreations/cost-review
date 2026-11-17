# ADR 0022: Recurring definitions and Expected occurrences

**Status:** Accepted
**Date:** 2026-11-16

## Context

Known future events such as rent, salary and insurance (CR-030–CR-036) must be
visible before they happen without contaminating Actual balances, summaries or
budgets.

## Decision

- A recurring definition stores account, kind, currency, schedule (weekly,
  monthly, quarterly or yearly with an interval), start and optional end date,
  optional category and provider, and a tolerance percentage.
- Expected amounts are versioned: each version applies from its effective date,
  so changing the rent from September does not rewrite earlier occurrences.
- Monthly schedules keep the start day, or the last day of shorter months.
- Expected occurrences are derived on every read and are never stored as
  transactions. Only decisions are stored: `confirmed` (linked to exactly one
  transaction) or `skipped`. A decision can be reopened.
- Confirmation either records a new Actual transaction with
  `source_type = 'recurring'` or links an existing one (for example an imported
  row). Candidate transactions on the same account and kind, within five days and
  inside the tolerance, are offered with a visible confidence; nothing is linked
  automatically.
- The deviation between expected and actual amount is stored and flagged when
  it exceeds the definition's tolerance. Unconfirmed past occurrences are shown
  as awaiting confirmation.

## Consequences

The tolerance is set per definition instead of globally (CR-032), because a
fixed rent and a variable electricity bill need different tolerances. Balances,
summaries and budgets remain based on Actual transactions only.
