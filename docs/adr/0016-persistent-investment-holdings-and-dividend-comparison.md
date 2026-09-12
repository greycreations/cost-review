# ADR 0016: Persistent investment holdings and historical dividend comparison

**Status:** Accepted

**Date:** 2026-09-12

## Context

The first Investments interface used one checkbox state both for browsing the Stockholm screener
and for the user's portfolio. A checkbox could therefore look like a saved holding while actually
disappearing when the tab was remounted. The compact holdings table also omitted market fields from
the screener, and the dividend calendar's relationship to saved holdings was unclear. Users also
need a transparent way to compare how much historical dividend each invested krona represented
without presenting that calculation as investment advice.

## Decision

- Screener checkboxes are temporary browser state. An explicit **Add holdings** action appends only
  new tickers to the user's persisted portfolio through the existing portfolio `PUT` endpoint.
- The saved, user- and environment-scoped portfolio position list is the sole source for the
  holdings table, dividend calendar and purchase allocation. Holdings have a separate checkbox
  selection and an explicit remove action that persists the replacement portfolio immediately.
- The holdings table repeats company, sector, price, daily, one-month, six-month and one-year
  change, trailing yield, dividend per share and dividend months from the screener. It additionally
  shows owned whole shares, position value and estimated annual dividend.
- The dividend calendar sums every trailing payment or ex-dividend record in each month for the
  saved share count. It remains a historical annual pattern rather than a schedule of confirmed
  future payments.
- A read-only top-ten dividend comparison ranks eligible catalog shares by trailing-12-month annual
  dividend per share divided by latest closing price. For the current purchase budget it shows the
  number of whole shares, capital invested and corresponding historical annual dividend.
- The comparison never adds or removes holdings, changes allocations or creates economic events.
  Its interface states that it is mechanical historical information and does not assess future
  dividend decisions, special-dividend recurrence, diversification, company risk, price loss, tax
  or fees.
- Browser calculations continue to use integer öre. Canonical persisted amounts remain decimal-safe
  at the API and database boundaries.

## Consequences

- No migration or new API route is required; existing portfolio positions acquire clearer product
  semantics and remain limited to the validated provider universe and existing 50-position cap.
- Added holdings and their calendar survive tab navigation, page closure and container restarts.
  Unsaved edits to owned share counts, allocations or budget still require **Save changes**.
- A high rank can reflect a special dividend or a falling share price and can therefore identify a
  yield trap rather than a durable future distribution. The comparison must retain its warning and
  historical labels whenever it is displayed.
