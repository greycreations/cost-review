# ADR 0010: Transaction sharing and analysis perspectives

## Status

Accepted for Release 1 Core MVP.

## Context

Cost Review must preserve the full economic event while allowing household
analysis to answer both “what happened in total?” and “what was my part?”. A
single transaction can contain splits with different owners or responsible
parties. Refunds and reimbursements must reduce the same owners' cost without
creating a second, contradictory allocation.

## Decision

- Sharing parties remain metadata under the installation's single local login;
  they are not application users.
- Percentage allocations are stored on each transaction split. The simple
  transaction form is an API convenience that writes its allocation to the
  transaction's single split. Split-level allocation is therefore the one
  canonical representation.
- An explicitly shared split must allocate more than zero percent to each named
  party and exactly 100 percent in total. Pydantic validates the API request and
  a deferred PostgreSQL constraint trigger independently protects the stored
  invariant across inserts, updates, and deletes.
- A split without explicit allocations is interpreted as 100 percent belonging
  to the current household/user. This preserves existing Ledger history and
  keeps ordinary unshared entry concise.
- A sharing party marked `is_self` contributes to the `my_share` perspective.
  Multiple self parties are additive, which permits future household setups
  without changing the historical allocation model.
- `total` and `my_share` are explicit analysis request parameters and are
  echoed in summary and analysis responses. Total remains the default for
  backward compatibility.
- Refunds and reimbursements inherit the original expense split proportions
  during derived analysis. The recovery event remains separately stored and
  linked; its source data is not rewritten.

## Consequences

- The full transaction amount and original allocation remain visible and
  auditable even when a dashboard shows only My Share.
- Editing an allocation changes derived results but does not replace or divide
  the source transaction into fictional cash events.
- Account/provider/category defaults for sharing are not introduced by this
  decision. They may prefill a future editor, but a transaction-level value
  will remain authoritative.
- Budget outcome, trend, and underlying entries use the same explicit
  perspective. The configured budget target is not silently rescaled; the
  selected perspective changes the derived actual and consumption. Future
  periodization must be calculated on the full amount before applying these
  percentages.

## Verification

PostgreSQL integration tests cover create and update, exact-total request
validation, the database constraint, Total versus My Share summary and
category analysis, and proportional recovery handling. Frontend tests prove
the selected perspective reaches both summary and analysis requests and that
an explicit household allocation is submitted without rounding through binary
floating-point arithmetic.
