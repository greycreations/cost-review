from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import Settings
from app.errors import ApiError
from app.investment_schemas import (
    DividendOpportunitiesRead,
    DividendOpportunityRead,
    InvestmentMarketStockRead,
)

MONEY_QUANTUM = Decimal("0.01")
PERCENT_QUANTUM = Decimal("0.01")
SOURCE_URL = "https://www.avanza.se/aktier/lista.html"
MAX_CANDIDATES = 40
MAX_GROWTH_FACTOR = Decimal("2")


@dataclass(frozen=True, slots=True)
class CachedOpportunities:
    snapshot: DividendOpportunitiesRead
    fingerprint: tuple[tuple[str, str, str], ...]
    fetched_at: datetime


class AvanzaDividendOpportunityService:
    """Validate dividend comparisons against current public Avanza stock information."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.avanza_fund_base_url.rstrip("/")
        self._cache_seconds = settings.market_data_cache_seconds
        self._timeout_seconds = settings.market_data_request_timeout_seconds
        self._cached: CachedOpportunities | None = None
        self._lock = asyncio.Lock()
        self._transport: httpx.AsyncBaseTransport | None = None

    async def get_opportunities(
        self,
        stocks: list[InvestmentMarketStockRead],
    ) -> DividendOpportunitiesRead:
        candidates = sorted(
            (
                stock
                for stock in stocks
                if stock.currency == "SEK"
                and stock.price > 0
                and stock.annual_dividend_per_share > 0
            ),
            key=lambda stock: (
                stock.annual_dividend_per_share / stock.price,
                stock.name.casefold(),
            ),
            reverse=True,
        )[:MAX_CANDIDATES]
        fingerprint = tuple(
            (stock.ticker, str(stock.price), str(stock.annual_dividend_per_share))
            for stock in candidates
        )
        now = datetime.now(UTC)
        cached = self._cached
        if cached and cached.fingerprint == fingerprint and self._fresh(cached.fetched_at, now):
            return cached.snapshot

        semaphore = asyncio.Semaphore(5)
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                follow_redirects=True,
                headers={"Accept": "application/json", "User-Agent": "Cost-Review/0.7.0"},
                transport=self._transport,
            ) as client:
                results = await asyncio.gather(
                    *(
                        self._validate_candidate(client, semaphore, stock)
                        for stock in candidates
                    ),
                    return_exceptions=True,
                )
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
            return self._stale_or_raise(cached, error)

        opportunities: list[DividendOpportunityRead] = []
        unavailable_count = 0
        for result in results:
            if isinstance(result, Exception):
                unavailable_count += 1
            elif result is not None:
                opportunities.append(result)

        if candidates and unavailable_count == len(candidates):
            return self._stale_or_raise(
                cached,
                httpx.HTTPError("All dividend validation requests failed"),
            )

        opportunities.sort(
            key=lambda opportunity: (
                -opportunity.dividend_yield,
                opportunity.name.casefold(),
            )
        )
        top_opportunities = opportunities[:10]
        snapshot = DividendOpportunitiesRead(
            source="Avanza",
            source_url=SOURCE_URL,
            retrieved_at=now,
            is_delayed=True,
            is_stale=False,
            candidate_count=len(candidates),
            qualified_count=len(opportunities),
            excluded_count=len(candidates) - unavailable_count - len(opportunities),
            unavailable_count=unavailable_count,
            opportunities=top_opportunities,
        )
        async with self._lock:
            self._cached = CachedOpportunities(
                snapshot=snapshot,
                fingerprint=fingerprint,
                fetched_at=now,
            )
        return snapshot

    async def _validate_candidate(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        stock: InvestmentMarketStockRead,
    ) -> DividendOpportunityRead | None:
        orderbook_id = await self._resolve_orderbook_id(client, semaphore, stock.ticker)
        if orderbook_id is None:
            return None
        async with semaphore:
            guide_response = await client.get(f"/_api/market-guide/stock/{orderbook_id}")
            guide_response.raise_for_status()
        guide = guide_response.json()
        if not isinstance(guide, dict) or not _guide_matches_stock(guide, stock.ticker):
            return None

        key_indicators = guide.get("keyIndicators")
        quote = guide.get("quote")
        listing = guide.get("listing")
        if not isinstance(key_indicators, dict) or not isinstance(quote, dict):
            return None
        if not isinstance(listing, dict) or str(listing.get("currency", "")).upper() != "SEK":
            return None

        price = _positive_decimal(quote.get("last"))
        ordinary_yield = _positive_decimal(key_indicators.get("ordinaryDirectYield"))
        dividend = key_indicators.get("dividend")
        payments_per_year = _positive_int(key_indicators.get("dividendsPerYear"), maximum=12)
        if (
            price is None
            or ordinary_yield is None
            or payments_per_year is None
            or not isinstance(dividend, dict)
            or _positive_decimal(dividend.get("amount")) is None
            or str(dividend.get("currencyCode", "")).upper() != "SEK"
        ):
            return None

        annual_dividend = (price * ordinary_yield).quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        if annual_dividend <= 0:
            return None

        async with semaphore:
            details_response = await client.get(
                f"/_api/market-guide/stock/{orderbook_id}/details"
            )
            details_response.raise_for_status()
        history = _ordinary_dividend_history(details_response.json())
        required_events = payments_per_year * 2
        if len(history) < required_events:
            return None

        previous_cycle = sum(history[:payments_per_year], Decimal("0"))
        prior_cycle = sum(history[payments_per_year:required_events], Decimal("0"))
        if previous_cycle <= 0 or prior_cycle <= 0:
            return None
        if annual_dividend > previous_cycle * MAX_GROWTH_FACTOR:
            return None
        if previous_cycle > prior_cycle * MAX_GROWTH_FACTOR:
            return None

        return DividendOpportunityRead(
            ticker=stock.ticker,
            name=stock.name,
            sector=stock.sector,
            currency="SEK",
            price=price.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP),
            annual_dividend_per_share=annual_dividend,
            dividend_yield=(ordinary_yield * Decimal("100")).quantize(
                PERCENT_QUANTUM,
                rounding=ROUND_HALF_UP,
            ),
            payments_per_year=payments_per_year,
            compared_cycles=2,
        )

    async def _resolve_orderbook_id(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        ticker: str,
    ) -> str | None:
        payload = {
            "query": ticker,
            "searchFilter": {"types": ["STOCK"]},
            "pagination": {"size": 10, "from": 0},
        }
        async with semaphore:
            response = await client.post("/_api/search/filtered-search", json=payload)
            response.raise_for_status()
        body = response.json()
        hits = body.get("hits", []) if isinstance(body, dict) else []
        for hit in hits:
            if not isinstance(hit, dict) or hit.get("type") != "STOCK":
                continue
            orderbook_id = str(hit.get("orderBookId", ""))
            if not orderbook_id.isascii() or not orderbook_id.isdigit():
                continue
            title = str(hit.get("title", ""))
            title_tickers = re.findall(r"\(([^()]*)\)", title)
            if any(
                _normalize_ticker(value) == _normalize_ticker(ticker)
                for value in title_tickers
            ):
                return orderbook_id
        return None

    def _fresh(self, fetched_at: datetime, now: datetime) -> bool:
        return now - fetched_at < timedelta(seconds=self._cache_seconds)

    @staticmethod
    def _stale_or_raise(
        cached: CachedOpportunities | None,
        error: Exception,
    ) -> DividendOpportunitiesRead:
        if cached:
            return cached.snapshot.model_copy(update={"is_stale": True})
        raise ApiError(
            502,
            "dividend_opportunities_unavailable",
            "Validated dividend opportunities could not be loaded from the public provider.",
        ) from error


def _normalize_ticker(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def _guide_matches_stock(payload: dict[str, Any], ticker: str) -> bool:
    listing = payload.get("listing")
    if not isinstance(listing, dict):
        return False
    provider_ticker = str(listing.get("tickerSymbol") or listing.get("shortName") or "")
    return _normalize_ticker(provider_ticker) == _normalize_ticker(ticker)


def _ordinary_dividend_history(payload: Any) -> list[Decimal]:
    if not isinstance(payload, dict):
        return []
    dividends = payload.get("dividends")
    if not isinstance(dividends, dict):
        return []
    events = dividends.get("pastEvents")
    if not isinstance(events, list):
        return []
    values: list[tuple[str, Decimal]] = []
    for event in events:
        if not isinstance(event, dict) or event.get("dividendType") != "ORDINARY":
            continue
        if str(event.get("currencyCode", "")).upper() != "SEK":
            continue
        amount = _non_negative_decimal(event.get("amount"))
        ex_date = str(event.get("exDate", ""))
        if amount is not None and re.fullmatch(r"\d{4}-\d{2}-\d{2}", ex_date):
            values.append((ex_date, amount))
    values.sort(key=lambda item: item[0], reverse=True)
    return [amount for _, amount in values]


def _positive_decimal(value: Any) -> Decimal | None:
    parsed = _non_negative_decimal(value)
    return parsed if parsed is not None and parsed > 0 else None


def _non_negative_decimal(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() and parsed >= 0 else None


def _positive_int(value: Any, maximum: int) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if 1 <= parsed <= maximum else None
