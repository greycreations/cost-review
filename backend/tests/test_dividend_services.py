from __future__ import annotations

import asyncio
import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.config import Settings
from app.dividend_services import AvanzaDividendOpportunityService
from app.errors import ApiError
from app.investment_schemas import InvestmentMarketStockRead, MarketChangesRead


def stock(ticker: str, name: str, price: str, dividend: str) -> InvestmentMarketStockRead:
    return InvestmentMarketStockRead(
        ticker=ticker,
        provider_symbol=f"{ticker.replace(' ', '-')}.ST",
        name=name,
        sector="real_estate",
        currency="SEK",
        price=Decimal(price),
        price_date=date(2026, 9, 11),
        changes=MarketChangesRead(
            one_day=Decimal("0"),
            one_month=None,
            six_months=None,
            one_year=Decimal("0"),
        ),
        annual_dividend_per_share=Decimal(dividend),
        dividend_yield=Decimal("0"),
        dividend_pattern=[],
        detail_level="summary",
    )


def guide(ticker: str, price: str, ordinary_yield: str, amount: str, frequency: int) -> dict:
    return {
        "listing": {
            "tickerSymbol": ticker,
            "currency": "SEK",
            "marketPlaceCode": "XSTO",
        },
        "keyIndicators": {
            "ordinaryDirectYield": ordinary_yield,
            "dividend": {"amount": amount, "currencyCode": "SEK"},
            "dividendsPerYear": frequency,
        },
        "quote": {"last": price},
    }


def details(amounts: list[str]) -> dict:
    return {
        "dividends": {
            "events": [],
            "pastEvents": [
                {
                    "exDate": f"{2026 - index:04d}-05-01",
                    "amount": amount,
                    "currencyCode": "SEK",
                    "dividendType": "ORDINARY",
                }
                for index, amount in enumerate(amounts)
            ],
        }
    }


def test_dividend_optimizer_excludes_bad_values_and_corrects_preference_share() -> None:
    orderbooks = {"LARK": "1", "ACRI B": "2", "NP3 PREF": "3"}
    guides = {
        "1": guide("LARK", "2.32", "0", "0", 1),
        "2": guide("ACRI B", "7.62", "0.4921", "3.75", 1),
        "3": guide("NP3 PREF", "30.20", "0.0662", "0.50", 4),
    }
    histories = {
        "2": details(["3.75", "0.70"]),
        "3": details(["0.50"] * 8),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("filtered-search"):
            query = json.loads(request.content)["query"]
            orderbook = orderbooks[query]
            return httpx.Response(
                200,
                json={
                    "hits": [
                        {
                            "type": "STOCK",
                            "title": f"Example company ({query})",
                            "orderBookId": orderbook,
                        }
                    ]
                },
            )
        orderbook = request.url.path.split("/")[-2 if request.url.path.endswith("details") else -1]
        return httpx.Response(
            200,
            json=(
                histories[orderbook]
                if request.url.path.endswith("details")
                else guides[orderbook]
            ),
        )

    service = AvanzaDividendOpportunityService(
        Settings(db_password="test-password", avanza_fund_base_url="https://provider.example")
    )
    service._transport = httpx.MockTransport(handler)

    snapshot = asyncio.run(
        service.get_opportunities(
            [
                stock("LARK", "Lärkberget AB (publ)", "2.32", "2.00"),
                stock("ACRI B", "Acrinova AB ser. B", "7.62", "3.75"),
                stock("NP3 PREF", "NP3 Fastigheter Pref", "30.20", "6.40"),
            ]
        )
    )

    assert snapshot.candidate_count == 3
    assert snapshot.qualified_count == 1
    assert snapshot.excluded_count == 2
    assert snapshot.unavailable_count == 0
    assert [item.ticker for item in snapshot.opportunities] == ["NP3 PREF"]
    assert snapshot.opportunities[0].annual_dividend_per_share == Decimal("2.00")
    assert snapshot.opportunities[0].dividend_yield == Decimal("6.62")


def test_dividend_optimizer_requires_an_exact_ticker_match() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "hits": [
                    {
                        "type": "STOCK",
                        "title": "Investor A (INVE A)",
                        "orderBookId": "1",
                    }
                ]
            },
        )

    service = AvanzaDividendOpportunityService(
        Settings(db_password="test-password", avanza_fund_base_url="https://provider.example")
    )
    service._transport = httpx.MockTransport(handler)

    snapshot = asyncio.run(
        service.get_opportunities([stock("INVE B", "Investor B", "314.80", "5.60")])
    )

    assert snapshot.opportunities == []
    assert snapshot.excluded_count == 1


def test_dividend_optimizer_reports_unavailability_instead_of_using_yahoo_fallback() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    service = AvanzaDividendOpportunityService(
        Settings(db_password="test-password", avanza_fund_base_url="https://provider.example")
    )
    service._transport = httpx.MockTransport(handler)

    with pytest.raises(ApiError) as error:
        asyncio.run(
            service.get_opportunities([stock("LARK", "Lärkberget AB", "2.32", "2.00")])
        )

    assert error.value.code == "dividend_opportunities_unavailable"
