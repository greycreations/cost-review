# ADR 0014: Dynamic Yahoo Stockholm equity universe

**Status:** Accepted
**Date:** 2026-09-11

## Context

The first production Investments release proved the server-side Yahoo adapter with nine curated
shares. That list did not satisfy the product goal of screening the shares traded in Stockholm.
Fetching one year of chart history for every instrument when the tab opens would be slow and would
create unnecessary provider load. Yahoo's interfaces are unofficial and its broad Stockholm result
also contains rights, subscription instruments and structured products that must not be presented as
ordinary shares.

## Decision

- The backend establishes a Yahoo cookie/crumb session and discovers equities with region `se`,
  exchange `STO` and Yahoo's eleven equity sectors. Results are cached for the configured market-data
  interval and deduplicated by provider symbol.
- Entries must have a SEK price, a company name and equity fundamentals. Temporary rights,
  subscription instruments and units are excluded by symbol classification. The response states
  that coverage is Yahoo-discovered rather than an official exchange entitlement.
- The default market-data response contains the complete lightweight catalog with price, daily and
  52-week change, sector and trailing dividend rate. One-month, six-month and dividend-event history
  is fetched from the chart endpoint only for up to 50 explicitly requested tickers and cached
  separately.
- Portfolio writes validate tickers against the current discovered universe. Existing display ticker
  identities remain compatible; PostgreSQL storage is widened to 32 characters.
- The browser searches and filters the full catalog but renders 50 rows at a time. Selecting a share
  triggers transparent detail enrichment for calculations and the dividend calendar.
- All market observations remain derived and non-canonical. They do not create or alter ledger,
  investment-trade, valuation-snapshot or dividend-income history.

## Consequences

- A keyless default installation exposes hundreds of Stockholm-traded share classes instead of a
  maintained shortlist while keeping initial latency and provider load bounded.
- Coverage depends on Yahoo's classification and may temporarily omit a newly listed company until
  Yahoo assigns sector and fundamental metadata. Official contractual completeness would require an
  entitled Nasdaq reference-data product or another provider.
- Yahoo can change its session or screener behavior. Existing stale-cache and honest unavailable
  states remain required; fictional fallback data is still forbidden outside the explicit preview.
