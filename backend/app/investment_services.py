from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Protocol
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.config import Settings
from app.errors import ApiError
from app.investment_schemas import (
    DividendPatternRead,
    InvestmentMarketDataRead,
    InvestmentMarketStockRead,
    InvestmentPortfolioRead,
    InvestmentPortfolioWrite,
    InvestmentPositionRead,
    MarketChangesRead,
)
from app.models import (
    AuditEvent,
    InvestmentPortfolioSettings,
    InvestmentPosition,
)


@dataclass(frozen=True, slots=True)
class StockDefinition:
    ticker: str
    provider_symbol: str
    name: str
    sector: str


STOCK_UNIVERSE = (
    StockDefinition("INVE B", "INVE-B.ST", "Investor B", "investment"),
    StockDefinition("VOLV B", "VOLV-B.ST", "Volvo B", "industry"),
    StockDefinition("SEB A", "SEB-A.ST", "SEB A", "finance"),
    StockDefinition("ATCO A", "ATCO-A.ST", "Atlas Copco A", "industry"),
    StockDefinition("ASSA B", "ASSA-B.ST", "Assa Abloy B", "industry"),
    StockDefinition("AXFO", "AXFO.ST", "Axfood", "consumer"),
    StockDefinition("TEL2 B", "TEL2-B.ST", "Tele2 B", "telecom"),
    StockDefinition("EPI A", "EPI-A.ST", "Epiroc A", "industry"),
    StockDefinition("SINCH", "SINCH.ST", "Sinch", "technology"),
)
STOCKS_BY_TICKER = {stock.ticker: stock for stock in STOCK_UNIVERSE}
MONEY_QUANTUM = Decimal("0.01")
PERCENT_QUANTUM = Decimal("0.01")
PORTFOLIO_MONEY_QUANTUM = Decimal("0.0001")
PORTFOLIO_PERCENT_QUANTUM = Decimal("0.0001")


def read_investment_portfolio(db: DbSession, user_id: int) -> InvestmentPortfolioRead:
    settings = db.get(InvestmentPortfolioSettings, user_id)
    positions = db.scalars(
        select(InvestmentPosition)
        .where(InvestmentPosition.user_id == user_id)
        .order_by(InvestmentPosition.investment_position_id)
    ).all()
    return InvestmentPortfolioRead(
        purchase_budget=settings.purchase_budget if settings else Decimal("0"),
        currency=settings.currency if settings else "SEK",
        positions=[
            InvestmentPositionRead(
                ticker=position.ticker,
                shares=position.shares,
                target_percentage=position.target_percentage,
            )
            for position in positions
        ],
        updated_at=settings.updated_at if settings else None,
    )


def save_investment_portfolio(
    db: DbSession,
    user_id: int,
    payload: InvestmentPortfolioWrite,
) -> InvestmentPortfolioRead:
    unknown_tickers = sorted(
        {position.ticker for position in payload.positions} - STOCKS_BY_TICKER.keys()
    )
    if unknown_tickers:
        raise ApiError(
            422,
            "unsupported_investment_ticker",
            "One or more investment tickers are not in the supported Stockholm universe.",
            [{"ticker": ticker} for ticker in unknown_tickers],
        )

    settings = db.get(InvestmentPortfolioSettings, user_id)
    action = "updated" if settings else "created"
    if settings is None:
        settings = InvestmentPortfolioSettings(user_id=user_id, currency="SEK")
        db.add(settings)
    settings.purchase_budget = payload.purchase_budget.quantize(
        PORTFOLIO_MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
    settings.updated_at = datetime.now(UTC)

    db.execute(delete(InvestmentPosition).where(InvestmentPosition.user_id == user_id))
    db.add_all(
        InvestmentPosition(
            user_id=user_id,
            ticker=position.ticker,
            shares=position.shares,
            target_percentage=position.target_percentage.quantize(
                PORTFOLIO_PERCENT_QUANTUM,
                rounding=ROUND_HALF_UP,
            ),
        )
        for position in payload.positions
    )
    db.add(
        AuditEvent(
            entity_type="investment_portfolio",
            entity_id=user_id,
            action=action,
            change_source="user",
            changes={
                "purchase_budget": str(settings.purchase_budget),
                "currency": "SEK",
                "positions": len(payload.positions),
            },
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ApiError(
            409,
            "investment_portfolio_conflict",
            "The investment portfolio could not be saved.",
        ) from error
    return read_investment_portfolio(db, user_id)


class MarketDataService(Protocol):
    async def get_snapshot(self) -> InvestmentMarketDataRead: ...


class CachedMarketDataService:
    def __init__(self, settings: Settings) -> None:
        self._cache_seconds = settings.market_data_cache_seconds
        self._timeout_seconds = settings.market_data_request_timeout_seconds
        self._cached: InvestmentMarketDataRead | None = None
        self._cache_lock = asyncio.Lock()
        self._retry_not_before: datetime | None = None

    async def get_snapshot(self) -> InvestmentMarketDataRead:
        now = datetime.now(UTC)
        if self._cache_is_fresh(now):
            return self._cached  # type: ignore[return-value]
        if self._cached and self._retry_not_before and now < self._retry_not_before:
            return self._cached

        async with self._cache_lock:
            now = datetime.now(UTC)
            if self._cache_is_fresh(now):
                return self._cached  # type: ignore[return-value]
            if self._cached and self._retry_not_before and now < self._retry_not_before:
                return self._cached
            try:
                snapshot = await self._fetch_snapshot(now)
            except ApiError:
                if self._cached is None:
                    raise
                self._cached = self._cached.model_copy(update={"is_stale": True})
                self._retry_not_before = now + timedelta(
                    seconds=min(self._cache_seconds, 900)
                )
                return self._cached
            self._cached = snapshot
            self._retry_not_before = None
            return snapshot

    def _cache_is_fresh(self, now: datetime) -> bool:
        return bool(
            self._cached
            and not self._cached.is_stale
            and (now - self._cached.retrieved_at).total_seconds() < self._cache_seconds
        )

    async def _fetch_snapshot(self, retrieved_at: datetime) -> InvestmentMarketDataRead:
        raise NotImplementedError


class YahooMarketDataService(CachedMarketDataService):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._base_url = f"{settings.yahoo_finance_base_url.rstrip('/')}/"

    async def _fetch_snapshot(self, retrieved_at: datetime) -> InvestmentMarketDataRead:
        stockholm_today = datetime.now(ZoneInfo("Europe/Stockholm")).date()
        semaphore = asyncio.Semaphore(3)
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            headers={
                "Accept": "application/json, text/plain, */*",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0 Safari/537.36 Cost-Review/0.4"
                ),
            },
        ) as client:
            results = await asyncio.gather(
                *(
                    self._fetch_stock(client, semaphore, stock, stockholm_today)
                    for stock in STOCK_UNIVERSE
                ),
                return_exceptions=True,
            )

        stocks: list[InvestmentMarketStockRead] = []
        unavailable: list[str] = []
        for definition, result in zip(STOCK_UNIVERSE, results, strict=True):
            if isinstance(result, BaseException):
                unavailable.append(definition.ticker)
            else:
                stocks.append(result)

        if unavailable:
            raise ApiError(
                502,
                "market_data_unavailable",
                "Yahoo Finance did not return a complete Stockholm snapshot.",
                [{"ticker": ticker} for ticker in unavailable],
            )

        return InvestmentMarketDataRead(
            source="Yahoo Finance",
            source_url="https://finance.yahoo.com/quote/%5EOMX/",
            exchange="Nasdaq Stockholm (XSTO)",
            retrieved_at=retrieved_at,
            data_date=max(stock.price_date for stock in stocks),
            is_delayed=True,
            is_stale=False,
            estimate_basis="trailing_12_months",
            universe_note="Curated starter universe of nine Nasdaq Stockholm shares.",
            stocks=stocks,
            unavailable_symbols=[],
        )

    async def _fetch_stock(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        definition: StockDefinition,
        as_of: date,
    ) -> InvestmentMarketStockRead:
        payload = await self._get_json(
            client,
            semaphore,
            f"v8/finance/chart/{definition.provider_symbol}",
            {
                "range": "1y",
                "interval": "1d",
                "events": "div,splits",
                "includeAdjustedClose": "true",
                "includePrePost": "false",
            },
        )
        prices, dividends = _parse_yahoo_chart(payload)
        return build_market_stock(definition, prices, dividends, as_of)

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        path: str,
        params: dict[str, str],
    ) -> object:
        retryable_statuses = {429, 500, 502, 503, 504}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with semaphore:
                    response = await client.get(path, params=params)
                if response.status_code in retryable_statuses and attempt < 2:
                    retry_after = response.headers.get("Retry-After")
                    delay = min(float(retry_after), 5.0) if retry_after else 0.25 * 2**attempt
                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, ValueError) as error:
                last_error = error
                if attempt == 2:
                    raise
                await asyncio.sleep(0.25 * 2**attempt)
        raise RuntimeError("Yahoo Finance request failed") from last_error


class EodhdMarketDataService(CachedMarketDataService):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._token = settings.eodhd_api_token.get_secret_value()
        self._base_url = f"{settings.eodhd_base_url.rstrip('/')}/"

    async def get_snapshot(self) -> InvestmentMarketDataRead:
        if not self._token:
            raise ApiError(
                503,
                "market_data_not_configured",
                "Market data is configured for EODHD, but EODHD_API_TOKEN is missing.",
            )
        return await super().get_snapshot()

    async def _fetch_snapshot(self, retrieved_at: datetime) -> InvestmentMarketDataRead:
        stockholm_today = datetime.now(ZoneInfo("Europe/Stockholm")).date()
        start = stockholm_today - timedelta(days=365)
        semaphore = asyncio.Semaphore(5)
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            headers={"User-Agent": "Cost-Review/0.4"},
        ) as client:
            results = await asyncio.gather(
                *(
                    self._fetch_stock(client, semaphore, stock, start, stockholm_today)
                    for stock in STOCK_UNIVERSE
                ),
                return_exceptions=True,
            )

        stocks: list[InvestmentMarketStockRead] = []
        unavailable: list[str] = []
        for definition, result in zip(STOCK_UNIVERSE, results, strict=True):
            if isinstance(result, BaseException):
                unavailable.append(definition.ticker)
            else:
                stocks.append(result)

        if unavailable:
            raise ApiError(
                502,
                "market_data_unavailable",
                "The market-data provider did not return a complete Stockholm snapshot.",
                [{"ticker": ticker} for ticker in unavailable],
            )

        return InvestmentMarketDataRead(
            source="EODHD",
            source_url="https://eodhd.com/exchange/ST",
            exchange="Nasdaq Stockholm (XSTO)",
            retrieved_at=retrieved_at,
            data_date=max(stock.price_date for stock in stocks),
            is_delayed=True,
            is_stale=False,
            estimate_basis="trailing_12_months",
            universe_note="Curated starter universe of nine Nasdaq Stockholm shares.",
            stocks=stocks,
            unavailable_symbols=[],
        )

    async def _fetch_stock(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        definition: StockDefinition,
        start: date,
        end: date,
    ) -> InvestmentMarketStockRead:
        prices, dividends = await asyncio.gather(
            self._get_json(
                client,
                semaphore,
                f"eod/{definition.provider_symbol}",
                {"from": start.isoformat(), "to": end.isoformat(), "period": "d", "fmt": "json"},
            ),
            self._get_json(
                client,
                semaphore,
                f"div/{definition.provider_symbol}",
                {"from": start.isoformat(), "to": end.isoformat(), "fmt": "json"},
            ),
        )
        if not isinstance(prices, list) or not prices:
            raise ValueError("empty price history")
        if not isinstance(dividends, list):
            raise ValueError("invalid dividend history")
        return build_market_stock(definition, prices, dividends, end)

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        path: str,
        params: dict[str, str],
    ) -> object:
        async with semaphore:
            response = await client.get(path, params={**params, "api_token": self._token})
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and (payload.get("error") or payload.get("message")):
            raise ValueError("provider returned an error")
        return payload


def create_market_data_service(settings: Settings) -> MarketDataService:
    if settings.market_data_provider == "eodhd":
        return EodhdMarketDataService(settings)
    return YahooMarketDataService(settings)


def _parse_yahoo_chart(payload: object) -> tuple[list[object], list[object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("chart"), dict):
        raise ValueError("invalid Yahoo Finance chart response")
    chart = payload["chart"]
    if chart.get("error"):
        raise ValueError("Yahoo Finance returned a chart error")
    results = chart.get("result")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise ValueError("Yahoo Finance returned no chart result")

    result = results[0]
    meta = result.get("meta")
    if not isinstance(meta, dict) or meta.get("currency") != "SEK":
        raise ValueError("Yahoo Finance returned an unexpected currency")
    timezone_name = meta.get("exchangeTimezoneName")
    try:
        exchange_timezone = ZoneInfo(timezone_name) if isinstance(timezone_name, str) else UTC
    except (KeyError, ValueError):
        exchange_timezone = UTC

    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    quotes = indicators.get("quote") if isinstance(indicators, dict) else None
    quote = quotes[0] if isinstance(quotes, list) and quotes and isinstance(quotes[0], dict) else {}
    closes = quote.get("close")
    if not isinstance(timestamps, list) or not isinstance(closes, list):
        raise ValueError("Yahoo Finance returned no price series")

    prices: list[object] = []
    for timestamp, close in zip(timestamps, closes, strict=False):
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            continue
        item_date = datetime.fromtimestamp(timestamp, exchange_timezone).date()
        prices.append({"date": item_date.isoformat(), "close": close})

    dividends: list[object] = []
    events = result.get("events")
    raw_dividends = events.get("dividends") if isinstance(events, dict) else None
    if isinstance(raw_dividends, dict):
        for item in raw_dividends.values():
            if not isinstance(item, dict):
                continue
            timestamp = item.get("date")
            if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
                continue
            item_date = datetime.fromtimestamp(timestamp, exchange_timezone).date()
            dividends.append({"date": item_date.isoformat(), "value": item.get("amount")})
    return prices, dividends


def build_market_stock(
    definition: StockDefinition,
    raw_prices: list[object],
    raw_dividends: list[object],
    as_of: date,
) -> InvestmentMarketStockRead:
    prices: list[tuple[date, Decimal]] = []
    for item in raw_prices:
        if not isinstance(item, dict):
            continue
        item_date = _parse_date(item.get("date"))
        close = _decimal(item.get("close"))
        if item_date and close is not None and close > 0:
            prices.append((item_date, close))
    prices.sort(key=lambda item: item[0])
    if not prices:
        raise ValueError("price history contained no valid closes")

    latest_date, latest_price = prices[-1]
    previous_price = prices[-2][1] if len(prices) > 1 else latest_price
    changes = MarketChangesRead(
        one_day=_percentage_change(latest_price, previous_price),
        one_month=_percentage_change(
            latest_price, _price_on_or_before(prices, as_of - timedelta(days=30))
        ),
        six_months=_percentage_change(
            latest_price, _price_on_or_before(prices, as_of - timedelta(days=183))
        ),
        one_year=_percentage_change(
            latest_price, _price_on_or_before(prices, as_of - timedelta(days=365))
        ),
    )

    trailing_start = as_of - timedelta(days=365)
    annual_dividend = Decimal("0")
    monthly_amounts: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    monthly_date_basis: dict[int, str] = {}
    for item in raw_dividends:
        if not isinstance(item, dict):
            continue
        ex_date = _parse_date(item.get("date"))
        amount = _decimal(item.get("value"))
        if not ex_date or not amount or amount <= 0 or not trailing_start <= ex_date <= as_of:
            continue
        annual_dividend += amount
        payment_date = _parse_date(item.get("paymentDate"))
        schedule_date = payment_date or ex_date
        date_basis = "payment_date" if payment_date else "ex_dividend_date"
        monthly_amounts[schedule_date.month] += amount
        previous_basis = monthly_date_basis.get(schedule_date.month)
        monthly_date_basis[schedule_date.month] = (
            "payment_date"
            if previous_basis in (None, "payment_date") and date_basis == "payment_date"
            else "ex_dividend_date"
        )

    annual_dividend = annual_dividend.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    dividend_yield = (
        (annual_dividend / latest_price * Decimal("100")).quantize(
            PERCENT_QUANTUM, rounding=ROUND_HALF_UP
        )
        if annual_dividend
        else Decimal("0")
    )
    pattern = [
        DividendPatternRead(
            month=month,
            amount=amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP),
            date_basis=monthly_date_basis[month],
        )
        for month, amount in sorted(monthly_amounts.items())
    ]
    return InvestmentMarketStockRead(
        ticker=definition.ticker,
        provider_symbol=definition.provider_symbol,
        name=definition.name,
        sector=definition.sector,
        currency="SEK",
        price=latest_price.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP),
        price_date=latest_date,
        changes=changes,
        annual_dividend_per_share=annual_dividend,
        dividend_yield=dividend_yield,
        dividend_pattern=pattern,
    )


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value or value == "0000-00-00":
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _price_on_or_before(prices: list[tuple[date, Decimal]], target: date) -> Decimal:
    for item_date, price in reversed(prices):
        if item_date <= target:
            return price
    return prices[0][1]


def _percentage_change(current: Decimal, previous: Decimal) -> Decimal:
    if previous <= 0:
        return Decimal("0")
    return ((current / previous - Decimal("1")) * Decimal("100")).quantize(
        PERCENT_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
