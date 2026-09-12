# ADR 0017: Public fund search and decimal holdings

**Status:** Accepted

**Date:** 2026-09-12

## Context

Ordinary Swedish mutual funds such as Länsförsäkringar Global Index, Avanza Zero and Avanza
Emerging Markets are not exchange-traded equities and are therefore not part of the Yahoo Stockholm
equity screener. A maintained shortlist would repeat the static-universe problem already removed
from the stock screener. Funds also use decimal units and NAV rather than whole shares and an
intraday exchange price.

## Decision

- Yahoo remains the equity provider. Fund search uses Avanza's public, unauthenticated search and
  fund-guide responses through a separate server-side, read-only adapter. No Avanza login,
  credential, order or account endpoint is used.
- The browser sends a fund name or ISIN to Cost Review. The backend requests one bounded page of at
  most 20 fund candidates and enriches only those candidates, with a concurrency limit of five.
  Search identities and fund detail are cached using the configured market-data cache duration.
- Provider failures never introduce sample data into production. Expired cached results may be
  returned with an explicit stale marker; otherwise the API reports honest unavailability.
- Funds are persisted by ISIN with `instrument_type=fund`. Existing investment positions migrate as
  `stock`. Position quantity uses `numeric(24,8)` and PostgreSQL enforces whole quantities for stock
  rows while allowing decimal fund units.
- Fund holdings show NAV date, one-month, six-month and one-year development, product fee, risk and
  position value. Fund purchase allocations use the allocated currency amount and show an estimated
  decimal unit count. Actual broker minimums, execution NAV and settlement timing remain outside the
  planner.
- Version 0.7.0 admits SEK-denominated funds only. Showing a non-SEK NAV as portfolio value without
  a dated FX observation would violate the application's currency boundary; broader fund currencies
  require a later FX-aware valuation design.
- Fund NAV and metadata remain derived external observations. They do not create or modify Ledger
  transactions, trades, dividends, realized results or valuation snapshots.

## Consequences

- The full public fund search is available without a static local catalog or API key, but the
  provider is unofficial and can change or rate-limit the public endpoints. The adapter is therefore
  isolated, cached and replaceable.
- ISIN gives a more durable portfolio identity than provider order-book ID; the provider ID is used
  only while retrieving details.
- Accumulating funds do not appear in the dividend calendar. The calendar remains based on saved
  stock dividend events, while fund total return is represented by NAV development.
