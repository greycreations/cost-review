# ADR 0013: Yahoo Finance as the default market-data adapter

**Status:** Accepted
**Date:** 2026-09-11

## Context

ADR 0012 introduced the Investments workspace with EODHD. Its free plan's fixed call allowance is
too restrictive for convenient use of a private, self-hosted watchlist. Yahoo Finance provides the
needed Stockholm closing-price history and dividend events without an API key, but the endpoints
are not a documented, contracted public API and can rate-limit or change without notice.

## Decision

- Yahoo Finance is the default market-data adapter. Each curated `.ST` symbol is requested through
  the server-side chart endpoint with one year of daily prices plus dividend and split events.
- Cost Review makes at most three concurrent Yahoo requests, retries transient HTTP and transport
  failures conservatively and caches a complete successful snapshot for a bounded period.
- A snapshot is accepted only when every curated symbol returns valid SEK price history. Partial
  provider responses are not presented as a complete market universe.
- If refresh fails after a previous success, the last in-process snapshot remains available with an
  explicit stale flag and a short retry cooldown. With no prior success, the API returns an honest
  unavailable state and the authenticated UI does not fall back to preview data.
- Yahoo dividend events provide historical ex-dividend dates. Annual dividend per share and the
  month pattern remain trailing-12-month estimates, not forecasts or confirmed payments.
- EODHD remains available through `MARKET_DATA_PROVIDER=eodhd` plus a server-side token. The
  frontend contract and portfolio calculations are provider-neutral.
- Provider observations remain derived external data. They never create or alter investment trades,
  valuation snapshots, dividend-income events or any other canonical economic history.

## Consequences

- A default installation can populate Investments without a provider account or secret.
- Operators accept that Yahoo access is unofficial and may be blocked or changed. Cache freshness,
  source, delay, market date and retrieval time remain visible so degraded data is never silent.
- The cache is process-local. A restart without Yahoo connectivity has no prior snapshot to serve;
  persistent market-observation storage remains a later enhancement.
- The curated universe, end-of-day character and historical dividend basis remain unchanged.
