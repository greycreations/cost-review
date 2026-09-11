from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.dependencies import Auth, CsrfAuth, DatabaseSession
from app.errors import ApiError
from app.investment_schemas import (
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
    supported_tickers = await service.get_supported_tickers()
    return save_investment_portfolio(
        db,
        auth.user.user_id,
        payload,
        supported_tickers,
    )
