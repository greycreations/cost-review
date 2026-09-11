from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

Ticker = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Money = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=4)]
Percentage = Annotated[Decimal, Field(ge=0, le=100, max_digits=7, decimal_places=4)]


class InvestmentPositionWrite(BaseModel):
    ticker: Ticker
    shares: int = Field(ge=0, le=1_000_000_000)
    target_percentage: Percentage = Decimal("0")

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return " ".join(value.upper().split())


class InvestmentPortfolioWrite(BaseModel):
    purchase_budget: Money = Decimal("0")
    positions: list[InvestmentPositionWrite] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_positions(self) -> InvestmentPortfolioWrite:
        tickers = [position.ticker for position in self.positions]
        if len(set(tickers)) != len(tickers):
            raise ValueError("positions must contain unique tickers")
        if sum((position.target_percentage for position in self.positions), Decimal("0")) > 100:
            raise ValueError("target percentages must total at most 100")
        return self


class InvestmentPositionRead(BaseModel):
    ticker: str
    shares: int
    target_percentage: Decimal


class InvestmentPortfolioRead(BaseModel):
    purchase_budget: Decimal
    currency: str
    positions: list[InvestmentPositionRead]
    updated_at: datetime | None


class MarketChangesRead(BaseModel):
    one_day: Decimal
    one_month: Decimal | None
    six_months: Decimal | None
    one_year: Decimal


class DividendPatternRead(BaseModel):
    month: int = Field(ge=1, le=12)
    amount: Decimal
    date_basis: Literal["payment_date", "ex_dividend_date"]


class InvestmentMarketStockRead(BaseModel):
    ticker: str
    provider_symbol: str
    name: str
    sector: str
    currency: str
    price: Decimal
    price_date: date
    changes: MarketChangesRead
    annual_dividend_per_share: Decimal
    dividend_yield: Decimal
    dividend_pattern: list[DividendPatternRead]
    detail_level: Literal["summary", "history"] = "history"


class InvestmentMarketDataRead(BaseModel):
    source: str
    source_url: str
    exchange: str
    retrieved_at: datetime
    data_date: date
    is_delayed: bool
    is_stale: bool
    estimate_basis: Literal["trailing_12_months"]
    universe_note: str
    stock_count: int = Field(default=0, ge=0)
    stocks: list[InvestmentMarketStockRead]
    unavailable_symbols: list[str]
