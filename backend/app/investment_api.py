from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.dependencies import Auth, CsrfAuth, DatabaseSession
from app.errors import ApiError
from app.fund_services import AvanzaFundDataService
from app.investment_schemas import (
    InvestmentFundDataRead,
    InvestmentMarketDataRead,
    InvestmentPortfolioRead,
    InvestmentPortfolioWrite,
)
from app.investment_services import (
    MarketDataService,
    read_investment_portfolio,
    save_investment_portfolio,
)

router = APIRouter(prefix="/investments", tags=["investments"])


@router.get("/market-data", response_model=InvestmentMarketDataRead)
async def get_market_data(
    _: Auth,
    request: Request,
    ticker: Annotated[list[str] | None, Query()] = None,
) -> InvestmentMarketDataRead:
    service: MarketDataService = request.app.state.market_data_service
    requested = tuple(dict.fromkeys(item.strip().upper() for item in ticker or [] if item.strip()))
    if len(requested) > 50 or any(len(item) > 32 for item in requested):
        raise ApiError(
            422,
            "too_many_investment_tickers",
            "At most 50 investment tickers can be enriched in one request.",
        )
    return await service.get_snapshot(requested)


@router.get("/fund-data", response_model=InvestmentFundDataRead)
async def get_fund_data(
    _: Auth,
    request: Request,
    query: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    isin: Annotated[list[str] | None, Query()] = None,
) -> InvestmentFundDataRead:
    service: AvanzaFundDataService = request.app.state.fund_data_service
    requested = tuple(dict.fromkeys(item.strip().upper() for item in isin or [] if item.strip()))
    if len(requested) > 50 or any(len(item) != 12 or not item.isalnum() for item in requested):
        raise ApiError(
            422,
            "invalid_fund_identifiers",
            "At most 50 valid fund ISINs can be enriched in one request.",
        )
    return await service.get_funds(query=query, isins=requested)


@router.get("/portfolio", response_model=InvestmentPortfolioRead)
def get_portfolio(auth: Auth, db: DatabaseSession) -> InvestmentPortfolioRead:
    return read_investment_portfolio(db, auth.user.user_id)


@router.put("/portfolio", response_model=InvestmentPortfolioRead)
async def put_portfolio(
    payload: InvestmentPortfolioWrite,
    auth: CsrfAuth,
    db: DatabaseSession,
    request: Request,
) -> InvestmentPortfolioRead:
    service: MarketDataService = request.app.state.market_data_service
    fund_service: AvanzaFundDataService = request.app.state.fund_data_service
    stock_positions = tuple(
        position.ticker for position in payload.positions if position.instrument_type == "stock"
    )
    fund_positions = tuple(
        position.ticker for position in payload.positions if position.instrument_type == "fund"
    )
    supported_tickers = await service.get_supported_tickers() if stock_positions else frozenset()
    supported_fund_isins = await fund_service.get_supported_isins(fund_positions)
    return save_investment_portfolio(
        db,
        auth.user.user_id,
        payload,
        supported_tickers,
        supported_fund_isins,
    )
