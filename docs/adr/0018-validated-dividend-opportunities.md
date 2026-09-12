# ADR 0018: Separately validated dividend opportunities

**Status:** Accepted

**Date:** 2026-09-12

## Context

Yahoo's trailing annual dividend fields are useful historical observations but can be misleading for
an optimizer. They may retain a discontinued payout, contain a one-off distribution, or associate an
ordinary-share dividend with a preference share. This produced implausible rankings such as a current
zero-dividend share at more than 80 percent and NP3 Pref with the ordinary share's 6.40 SEK annual
dividend instead of the preference share's 2.00 SEK.

## Decision

- Yahoo remains the Stockholm equity catalog and preliminary candidate source. The backend selects
  at most the 40 highest positive trailing-yield observations so provider work stays bounded.
- A separate server-side, read-only Avanza adapter searches each ticker and requires an exact ticker
  match in both search and stock guide data. No login, account, credential or trading endpoint is used.
- A ranked candidate needs a positive current `ordinaryDirectYield`, a positive ordinary payout in
  SEK and at least two complete payout cycles in ordinary historical events. Special distributions
  and zero payout cycles are not treated as recurring yield.
- A current annual amount or the latest completed cycle may not exceed the preceding comparable cycle
  by more than a factor of two. This stability rule intentionally excludes extraordinary jumps from
  a mechanical income comparison; dividend cuts remain visible if the other requirements are met.
- The ranked price and annual amount are calculated with decimal arithmetic from Avanza's delayed
  price and current ordinary yield. At most ten qualified rows are returned.
- Validation is concurrency-bounded and cached for the configured market-data duration. A fully
  failed refresh may serve a clearly stale previous result; without a previous result the endpoint
  reports unavailability and the browser does not reconstruct the old Yahoo-only ranking.

## Consequences

- The comparison is materially more conservative and no longer treats all trailing cash events as
  recurring future income. A newly listed payer or a genuine dividend increase above the stability
  threshold will be absent until enough comparable history exists.
- The result is still not a forecast or recommendation. Boards can change or cancel dividends after
  either provider observation, and the comparison does not model company risk, tax, fees or price loss.
- Avanza's public endpoints are unofficial and replaceable. Source, freshness and coverage counts are
  exposed so partial or stale validation is visible rather than implied to be complete market truth.
