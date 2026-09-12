from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import Settings
from app.errors import ApiError
from app.investment_schemas import (
    InvestmentFundDataRead,
    InvestmentFundRead,
    MarketChangesRead,
)

MONEY_QUANTUM = Decimal("0.0001")
PERCENT_QUANTUM = Decimal("0.01")
SOURCE_URL = "https://www.avanza.se/fonder/lista.html"


@dataclass(frozen=True, slots=True)
class CachedFund:
    fund: InvestmentFundRead
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class CachedSearch:
    provider_ids: tuple[str, ...]
    fetched_at: datetime


class AvanzaFundDataService:
    """Read-only adapter for Avanza's public, unauthenticated fund information."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.avanza_fund_base_url.rstrip("/")
        self._cache_seconds = settings.market_data_cache_seconds
        self._timeout_seconds = settings.market_data_request_timeout_seconds
        self._fund_cache: dict[str, CachedFund] = {}
        self._provider_id_by_isin: dict[str, str] = {}
        self._search_cache: dict[str, CachedSearch] = {}
        self._lock = asyncio.Lock()
        self._transport: httpx.AsyncBaseTransport | None = None

    async def get_funds(
        self,
        query: str | None = None,
        isins: tuple[str, ...] = (),
    ) -> InvestmentFundDataRead:
        normalized_query = " ".join((query or "").split())
        normalized_isins = tuple(dict.fromkeys(item.strip().upper() for item in isins))
        now = datetime.now(UTC)
        provider_ids: list[str] = []
        unavailable: list[str] = []
        stale = False

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                follow_redirects=True,
                headers={"Accept": "application/json", "User-Agent": "Cost-Review/0.7.0"},
                transport=self._transport,
            ) as client:
                if normalized_query:
                    ids, search_stale = await self._search(client, normalized_query, now)
                    provider_ids.extend(ids)
                    stale = stale or search_stale
                for isin in normalized_isins:
                    provider_id, lookup_stale = await self._resolve_isin(client, isin, now)
                    stale = stale or lookup_stale
                    if provider_id is None:
                        unavailable.append(isin)
                    else:
                        provider_ids.append(provider_id)

                unique_ids = tuple(dict.fromkeys(provider_ids))
                semaphore = asyncio.Semaphore(5)
                results = await asyncio.gather(
                    *(
                        self._fund_for_id(client, semaphore, provider_id, now)
                        for provider_id in unique_ids
                    ),
                    return_exceptions=True,
                )
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
            raise ApiError(
                502,
                "fund_data_unavailable",
                "Fund data could not be loaded from the public provider.",
            ) from error

        funds: list[InvestmentFundRead] = []
        for provider_id, result in zip(unique_ids, results, strict=True):
            if isinstance(result, Exception):
                cached = self._fund_cache.get(provider_id)
                if cached is None:
                    continue
                funds.append(cached.fund)
                stale = True
            else:
                fund, fund_stale = result
                funds.append(fund)
                stale = stale or fund_stale

        if normalized_query and not funds and provider_ids:
            raise ApiError(
                502,
                "fund_data_unavailable",
                "Fund details could not be loaded from the public provider.",
            )

        # Cost Review cannot value non-SEK holdings without an observed FX rate. Keep the
        # first fund release honest by exposing only SEK-denominated funds to the planner.
        funds = [fund for fund in funds if fund.currency == "SEK"]
        by_isin = {fund.isin: fund for fund in funds}
        unavailable.extend(isin for isin in normalized_isins if isin not in by_isin)
        unavailable = list(dict.fromkeys(unavailable))
        ordered_funds = [by_isin[isin] for isin in normalized_isins if isin in by_isin]
        ordered_funds.extend(fund for fund in funds if fund.isin not in normalized_isins)
        ordered_funds = list({fund.isin: fund for fund in ordered_funds}.values())
        data_date = max((fund.nav_date for fund in ordered_funds), default=None)
        return InvestmentFundDataRead(
            source="Avanza · publik fondinformation",
            source_url=SOURCE_URL,
            retrieved_at=now,
            data_date=data_date,
            is_delayed=True,
            is_stale=stale,
            query=normalized_query or None,
            result_count=len(ordered_funds),
            funds=ordered_funds,
            unavailable_isins=unavailable,
        )

    async def get_supported_isins(self, isins: tuple[str, ...]) -> frozenset[str]:
        if not isins:
            return frozenset()
        snapshot = await self.get_funds(isins=isins)
        return frozenset(fund.isin for fund in snapshot.funds)

    async def _search(
        self,
        client: httpx.AsyncClient,
        query: str,
        now: datetime,
    ) -> tuple[tuple[str, ...], bool]:
        key = query.casefold()
        cached = self._search_cache.get(key)
        if cached and self._fresh(cached.fetched_at, now):
            return cached.provider_ids, False
        payload = {
            "query": query,
            "searchFilter": {"types": ["FUND"]},
            "pagination": {"size": 20, "from": 0},
        }
        try:
            response = await client.post("/_api/search/filtered-search", json=payload)
            response.raise_for_status()
            body = response.json()
            hits = body.get("hits", []) if isinstance(body, dict) else []
            provider_ids = tuple(
                str(hit["orderBookId"])
                for hit in hits
                if isinstance(hit, dict)
                and hit.get("type") == "FUND"
                and str(hit.get("orderBookId", "")).isascii()
                and str(hit.get("orderBookId", "")).isdigit()
            )
            self._search_cache[key] = CachedSearch(provider_ids=provider_ids, fetched_at=now)
            return provider_ids, False
        except (httpx.HTTPError, ValueError, TypeError):
            if cached:
                return cached.provider_ids, True
            raise

    async def _resolve_isin(
        self,
        client: httpx.AsyncClient,
        isin: str,
        now: datetime,
    ) -> tuple[str | None, bool]:
        known_id = self._provider_id_by_isin.get(isin)
        if known_id:
            return known_id, False
        provider_ids, stale = await self._search(client, isin, now)
        semaphore = asyncio.Semaphore(3)
        for provider_id in provider_ids:
            try:
                fund, fund_stale = await self._fund_for_id(client, semaphore, provider_id, now)
            except (httpx.HTTPError, ValueError, TypeError, KeyError):
                continue
            if fund.isin == isin:
                return provider_id, stale or fund_stale
        return None, stale

    async def _fund_for_id(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        provider_id: str,
        now: datetime,
    ) -> tuple[InvestmentFundRead, bool]:
        cached = self._fund_cache.get(provider_id)
        if cached and self._fresh(cached.fetched_at, now):
            return cached.fund, False
        try:
            async with semaphore:
                response = await client.get(f"/_api/fund-guide/guide/{provider_id}")
                response.raise_for_status()
            fund = _parse_fund(provider_id, response.json())
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            if cached:
                return cached.fund, True
            raise
        async with self._lock:
            self._fund_cache[provider_id] = CachedFund(fund=fund, fetched_at=now)
            self._provider_id_by_isin[fund.isin] = provider_id
        return fund, False

    def _fresh(self, fetched_at: datetime, now: datetime) -> bool:
        return now - fetched_at < timedelta(seconds=self._cache_seconds)


def _decimal(value: Any, quantum: Decimal = PERCENT_QUANTUM) -> Decimal:
    try:
        parsed = Decimal(str(value))
        if not parsed.is_finite():
            raise InvalidOperation
        return parsed.quantize(quantum, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0").quantize(quantum)


def _optional_int(value: Any, minimum: int, maximum: int) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if minimum <= parsed <= maximum else None


def _parse_fund(provider_id: str, payload: Any) -> InvestmentFundRead:
    if not isinstance(payload, dict):
        raise ValueError("Unexpected fund payload")
    isin = str(payload["isin"]).strip().upper()
    if len(isin) != 12 or not isin.isalnum():
        raise ValueError("Fund payload has no valid ISIN")
    nav_date = datetime.fromisoformat(str(payload["navDate"]).replace("Z", "+00:00")).date()
    categories = payload.get("categories")
    category = str(categories[0]) if isinstance(categories, list) and categories else "Övrigt"
    admin_company = payload.get("adminCompany")
    company = str(admin_company.get("name", "")) if isinstance(admin_company, dict) else ""
    return InvestmentFundRead(
        isin=isin,
        provider_id=provider_id,
        name=str(payload["name"]).strip(),
        category=category,
        fund_type=str(payload.get("fundTypeName") or "Fond"),
        fund_company=company,
        currency=str(payload.get("currency") or "SEK").upper(),
        nav=_decimal(payload.get("nav"), MONEY_QUANTUM),
        nav_date=nav_date,
        changes=MarketChangesRead(
            one_day=_decimal(payload.get("developmentOneDay")),
            one_month=_decimal(payload.get("developmentOneMonth")),
            six_months=_decimal(payload.get("developmentSixMonths")),
            one_year=_decimal(payload.get("developmentOneYear")),
        ),
        product_fee=_decimal(payload.get("productFee")),
        management_fee=_decimal(payload.get("managementFee")),
        risk=_optional_int(payload.get("risk"), 1, 7),
        rating=_optional_int(payload.get("rating"), 1, 5),
        index_fund=bool(payload.get("indexFund", False)),
    )
