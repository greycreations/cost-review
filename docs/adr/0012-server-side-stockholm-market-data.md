# ADR 0012: Server-side Stockholm market data and investment planning

**Status:** Superseded by ADR 0013
**Date:** 2026-09-11

## Context

The Investments workspace needs authentic Stockholm prices, price development and dividend
history. It also needs to remember a user's selected shares, whole-share holdings, monthly purchase
budget and target percentages without weakening the Production/Demo-Test boundary. Provider tokens
must not be exposed to the browser, and unavailable external data must not be confused with the
illustrative development preview.

## Decision

- EODHD is the first market-data provider. The backend calls its end-of-day and dividend endpoints
  with `EODHD_API_TOKEN`; the frontend never receives the token.
- The first enabled universe is nine curated, well-known Nasdaq Stockholm shares. Provider symbols
  and stable sector metadata are maintained server-side. The provider abstraction may later switch
  to exchange-wide discovery without changing the frontend contract.
- Closing-price history supplies the latest price and 1-day, 1-month, 6-month and 1-year changes.
  Provider decimal values are parsed as `Decimal` before calculations or serialization.
- Dividend per share is the sum of provider records from the trailing 12 months. The calendar uses
  payment date when supplied and otherwise the ex-dividend date. The interface labels this as an
  indicative historical pattern, never a confirmed future payment schedule.
- A six-hour in-process cache is the default to limit provider calls. The response exposes the
  provider, latest market date, retrieval time, delay flag and estimation basis.
- Selected tickers, whole-share counts, target percentages and purchase budget are stored in new
  PostgreSQL tables per user. They inherit the physical Production/Demo-Test data-plane boundary,
  backups and test-reset behavior. PostgreSQL and backend validation cap total allocation at 100%.
- Provider observations remain derived external data. They are not persisted as transactions,
  valuation snapshots, realized income or historical economic events.
- If the provider token is absent or the complete snapshot cannot be loaded, the authenticated app
  shows a configuration/error state and does not fall back to sample values. Illustrative values
  remain available only in the explicit local development preview.

## Consequences

- Operators who want the tab must obtain and configure one provider token. Production and Test can
  read the same public-market feed while their personal planning data remains physically isolated.
- The data is delayed end-of-day information and is unsuitable for order execution. Provider terms,
  plan limits and coverage apply.
- The curated universe keeps initial latency and call volume predictable. Exchange-wide screening,
  confirmed forward dividend calendars, multiple currencies and lot-level cost basis remain later
  work.
