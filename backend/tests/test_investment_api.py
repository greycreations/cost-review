from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import ApiError
from app.investment_schemas import InvestmentMarketDataRead
from app.investment_services import (
    STOCKS_BY_TICKER,
    EodhdMarketDataService,
    YahooMarketDataService,
    _build_yahoo_catalog_stock,
    _parse_yahoo_screener,
    build_market_stock,
    create_market_data_service,
)

SETUP = {
    "username": "investment-owner",
    "password": "correct horse battery staple",
    "settings": {
        "language": "sv",
        "region": "SE",
        "base_currency": "SEK",
        "timezone": "Europe/Stockholm",
        "date_format": "YYYY-MM-DD",
        "number_format": "space-comma",
        "week_start": "monday",
    },
}


class SupportedMarketDataStub:
    async def get_supported_tickers(self) -> frozenset[str]:
        return frozenset(STOCKS_BY_TICKER)

    async def get_snapshot(self, tickers: tuple[str, ...] = ()) -> InvestmentMarketDataRead:
        raise AssertionError(f"unexpected market snapshot request: {tickers}")


def authenticate(client: TestClient, settings: Settings) -> dict[str, str]:
    response = client.post("/api/v1/setup", json=SETUP)
    assert response.status_code == 201
    csrf = client.cookies.get(settings.csrf_cookie_name)
    assert csrf
    client.app.state.market_data_service = SupportedMarketDataStub()
    return {"X-CSRF-Token": csrf}


def test_market_calculations_use_decimal_closes_and_trailing_dividends() -> None:
    stock = build_market_stock(
        STOCKS_BY_TICKER["INVE B"],
        [
            {"date": "2025-09-11", "close": "100.00"},
            {"date": "2026-03-11", "close": "110.00"},
            {"date": "2026-08-11", "close": "120.00"},
            {"date": "2026-09-10", "close": "126.00"},
            {"date": "2026-09-11", "close": "127.00"},
        ],
        [
            {
                "date": "2026-03-20",
                "paymentDate": "2026-03-28",
                "value": "3.00",
            },
            {"date": "2026-09-01", "value": "5.00"},
            {"date": "2025-08-01", "value": "99.00"},
        ],
        date(2026, 9, 11),
    )

    assert stock.price == Decimal("127.00")
    assert stock.changes.one_day == Decimal("0.79")
    assert stock.changes.one_month == Decimal("5.83")
    assert stock.changes.six_months == Decimal("15.45")
    assert stock.changes.one_year == Decimal("27.00")
    assert stock.annual_dividend_per_share == Decimal("8.00")
    assert stock.dividend_yield == Decimal("6.30")
    assert [(item.month, item.date_basis) for item in stock.dividend_pattern] == [
        (3, "payment_date"),
        (9, "ex_dividend_date"),
    ]


def test_eodhd_requests_stay_server_side_and_use_the_documented_api_paths() -> None:
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if "/eod/" in request.url.path:
            return httpx.Response(
                200,
                json=[
                    {"date": "2026-09-10", "close": "126.00"},
                    {"date": "2026-09-11", "close": "127.00"},
                ],
            )
        return httpx.Response(200, json=[])

    service = EodhdMarketDataService(
        Settings(
            db_password="test-password",
            eodhd_api_token="server-secret",
            eodhd_base_url="https://provider.example/api",
        )
    )

    async def fetch_one():
        async with httpx.AsyncClient(
            base_url=service._base_url,
            transport=httpx.MockTransport(handler),
        ) as client:
            return await service._fetch_stock(
                client,
                asyncio.Semaphore(1),
                STOCKS_BY_TICKER["INVE B"],
                date(2025, 9, 6),
                date(2026, 9, 11),
            )

    stock = asyncio.run(fetch_one())

    assert stock.price == Decimal("127.00")
    assert len(requested_urls) == 2
    assert all("api_token=server-secret" in url for url in requested_urls)
    assert any("/api/eod/INVE-B.ST" in url for url in requested_urls)
    assert any("/api/div/INVE-B.ST" in url for url in requested_urls)


def test_yahoo_is_default_and_parses_one_chart_request_per_stock() -> None:
    requested_urls: list[str] = []
    first_timestamp = int(datetime(2026, 9, 10, 7, tzinfo=UTC).timestamp())
    second_timestamp = int(datetime(2026, 9, 11, 7, tzinfo=UTC).timestamp())
    dividend_timestamp = int(datetime(2026, 3, 20, 8, tzinfo=UTC).timestamp())

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "chart": {
                    "error": None,
                    "result": [
                        {
                            "meta": {
                                "currency": "SEK",
                                "exchangeTimezoneName": "Europe/Stockholm",
                            },
                            "timestamp": [first_timestamp, second_timestamp],
                            "indicators": {"quote": [{"close": [126.0, 127.0]}]},
                            "events": {
                                "dividends": {
                                    str(dividend_timestamp): {
                                        "amount": 5.2,
                                        "date": dividend_timestamp,
                                    }
                                }
                            },
                        }
                    ],
                }
            },
        )

    settings = Settings(
        db_password="test-password",
        yahoo_finance_base_url="https://provider.example",
    )
    assert isinstance(create_market_data_service(settings), YahooMarketDataService)
    service = YahooMarketDataService(settings)

    async def fetch_one():
        async with httpx.AsyncClient(
            base_url=service._base_url,
            transport=httpx.MockTransport(handler),
        ) as client:
            return await service._fetch_stock(
                client,
                asyncio.Semaphore(1),
                STOCKS_BY_TICKER["INVE B"],
                date(2026, 9, 11),
            )

    stock = asyncio.run(fetch_one())

    assert stock.price == Decimal("127.00")
    assert stock.annual_dividend_per_share == Decimal("5.20")
    assert [(item.month, item.date_basis) for item in stock.dividend_pattern] == [
        (3, "ex_dividend_date")
    ]
    assert len(requested_urls) == 1
    assert "/v8/finance/chart/INVE-B.ST" in requested_urls[0]
    assert "events=div%2Csplits" in requested_urls[0]
    assert "api_token" not in requested_urls[0]


def test_yahoo_screener_builds_summary_stocks_and_rejects_temporary_instruments() -> None:
    payload = {
        "finance": {
            "error": None,
            "result": [
                {
                    "total": 2,
                    "quotes": [
                        {"symbol": "INVE-B.ST"},
                        {"symbol": "BIOSGN-BTA.ST"},
                    ],
                }
            ],
        }
    }
    quotes, total = _parse_yahoo_screener(payload)
    assert total == 2
    assert len(quotes) == 2

    common = {
        "shortName": "Investor AB ser. B",
        "currency": "SEK",
        "regularMarketPrice": "402.55",
        "regularMarketTime": int(datetime(2026, 9, 11, 15, tzinfo=UTC).timestamp()),
        "regularMarketChangePercent": "0.42",
        "fiftyTwoWeekChangePercent": "14.25",
        "trailingAnnualDividendRate": "5.60",
        "bookValue": "354.448",
    }
    stock = _build_yahoo_catalog_stock(
        {**common, "symbol": "INVE-B.ST"},
        "financial_services",
    )
    assert stock is not None
    assert stock.ticker == "INVE B"
    assert stock.detail_level == "summary"
    assert stock.changes.one_month is None
    assert stock.annual_dividend_per_share == Decimal("5.60")

    temporary = _build_yahoo_catalog_stock(
        {**common, "symbol": "BIOSGN-BTA.ST"},
        "healthcare",
    )
    assert temporary is None


def test_expired_snapshot_is_returned_as_stale_when_refresh_fails() -> None:
    settings = Settings(
        db_password="test-password",
        market_data_cache_seconds=60,
    )
    service = YahooMarketDataService(settings)
    stock = build_market_stock(
        STOCKS_BY_TICKER["INVE B"],
        [{"date": "2026-09-10", "close": "127.00"}],
        [],
        date(2026, 9, 11),
    )
    service._cached = InvestmentMarketDataRead(
        source="Yahoo Finance",
        source_url="https://finance.yahoo.com/",
        exchange="Nasdaq Stockholm (XSTO)",
        retrieved_at=datetime.now(UTC) - timedelta(hours=1),
        data_date=stock.price_date,
        is_delayed=True,
        is_stale=False,
        estimate_basis="trailing_12_months",
        universe_note="Test universe.",
        stocks=[stock],
        unavailable_symbols=[],
    )

    async def fail_refresh(_: datetime) -> InvestmentMarketDataRead:
        raise ApiError(502, "market_data_unavailable", "Provider unavailable.")

    service._fetch_snapshot = fail_refresh  # type: ignore[method-assign]
    snapshot = asyncio.run(service.get_snapshot())

    assert snapshot.is_stale is True
    assert snapshot.stocks[0].price == Decimal("127.00")
    assert service._retry_not_before is not None


def test_portfolio_is_authenticated_csrf_protected_and_decimal_safe(
    client: TestClient,
    settings: Settings,
) -> None:
    headers = authenticate(client, settings)

    initial = client.get("/api/v1/investments/portfolio")
    assert initial.status_code == 200
    assert initial.json() == {
        "purchase_budget": "0",
        "currency": "SEK",
        "positions": [],
        "updated_at": None,
    }

    payload = {
        "purchase_budget": "12500.50",
        "positions": [
            {"ticker": "inve b", "shares": 42, "target_percentage": "30.25"},
            {"ticker": "AXFO", "shares": 8, "target_percentage": "15.75"},
        ],
    }
    rejected = client.put("/api/v1/investments/portfolio", json=payload)
    assert rejected.status_code == 403

    saved = client.put("/api/v1/investments/portfolio", headers=headers, json=payload)
    assert saved.status_code == 200
    assert saved.json()["purchase_budget"] == "12500.5000"
    assert saved.json()["positions"] == [
        {"ticker": "INVE B", "shares": 42, "target_percentage": "30.2500"},
        {"ticker": "AXFO", "shares": 8, "target_percentage": "15.7500"},
    ]

    reloaded = client.get("/api/v1/investments/portfolio")
    assert reloaded.json() == saved.json()


def test_portfolio_rejects_unknown_tickers_and_overallocation(
    client: TestClient,
    settings: Settings,
) -> None:
    headers = authenticate(client, settings)

    unknown = client.put(
        "/api/v1/investments/portfolio",
        headers=headers,
        json={
            "purchase_budget": "1000",
            "positions": [{"ticker": "UNKNOWN", "shares": 1, "target_percentage": "10"}],
        },
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "unsupported_investment_ticker"

    overallocated = client.put(
        "/api/v1/investments/portfolio",
        headers=headers,
        json={
            "purchase_budget": "1000",
            "positions": [
                {"ticker": "INVE B", "shares": 1, "target_percentage": "60"},
                {"ticker": "AXFO", "shares": 1, "target_percentage": "60"},
            ],
        },
    )
    assert overallocated.status_code == 422
    assert overallocated.json()["error"]["code"] == "validation_failed"


def test_market_data_never_falls_back_to_samples_when_unconfigured(
    client: TestClient,
    settings: Settings,
) -> None:
    authenticate(client, settings)
    client.app.state.market_data_service = EodhdMarketDataService(
        Settings(
            db_password="test-password",
            market_data_provider="eodhd",
            eodhd_api_token="",
        )
    )

    response = client.get("/api/v1/investments/market-data")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "market_data_not_configured"


def test_demo_reset_removes_investment_planning_state(
    client: TestClient,
    settings: Settings,
) -> None:
    headers = authenticate(client, settings)
    saved = client.put(
        "/api/v1/investments/portfolio",
        headers=headers,
        json={
            "purchase_budget": "5000",
            "positions": [{"ticker": "INVE B", "shares": 10, "target_percentage": "100"}],
        },
    )
    assert saved.status_code == 200

    reset = client.post(
        "/api/v1/test/reset",
        headers=headers,
        json={"confirmation": "DELETE ALL TEST DATA"},
    )
    assert reset.status_code == 200
    assert client.get("/api/v1/investments/portfolio").json()["positions"] == []
