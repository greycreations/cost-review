from __future__ import annotations

from fastapi import APIRouter, Request

from app.dependencies import Auth, CsrfAuth, DatabaseSession
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
async def get_market_data(_: Auth, request: Request) -> InvestmentMarketDataRead:
    service: MarketDataService = request.app.state.market_data_service
    return await service.get_snapshot()


@router.get("/portfolio", response_model=InvestmentPortfolioRead)
def get_portfolio(auth: Auth, db: DatabaseSession) -> InvestmentPortfolioRead:
    return read_investment_portfolio(db, auth.user.user_id)


@router.put("/portfolio", response_model=InvestmentPortfolioRead)
def put_portfolio(
    payload: InvestmentPortfolioWrite,
    auth: CsrfAuth,
    db: DatabaseSession,
) -> InvestmentPortfolioRead:
    return save_investment_portfolio(db, auth.user.user_id, payload)
