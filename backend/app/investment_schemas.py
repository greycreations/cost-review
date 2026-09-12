from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

Ticker = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Money = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=4)]
Percentage = Annotated[Decimal, Field(ge=0, le=100, max_digits=7, decimal_places=4)]
HoldingQuantity = Annotated[Decimal, Field(ge=0, le=1_000_000_000, max_digits=24, decimal_places=8)]
InstrumentType = Literal["stock", "fund"]


class InvestmentPositionWrite(BaseModel):
    instrument_type: InstrumentType = "stock"
    ticker: Ticker
    shares: HoldingQuantity
    target_percentage: Percentage = Decimal("0")

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return " ".join(value.upper().split())

    @model_validator(mode="after")
    def validate_quantity(self) -> InvestmentPositionWrite:
        if self.instrument_type == "stock" and self.shares != self.shares.to_integral_value():
            raise ValueError("stock positions must contain whole shares")
        return self


class InvestmentPortfolioWrite(BaseModel):
    purchase_budget: Money = Decimal("0")
    positions: list[InvestmentPositionWrite] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_positions(self) -> InvestmentPortfolioWrite:
        identifiers = [(position.instrument_type, position.ticker) for position in self.positions]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("positions must contain unique instruments")
        if sum((position.target_percentage for position in self.positions), Decimal("0")) > 100:
            raise ValueError("target percentages must total at most 100")
        return self


class InvestmentPositionRead(BaseModel):
    instrument_type: InstrumentType
    ticker: str
    shares: Decimal
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


class DividendOpportunityRead(BaseModel):
    ticker: str
    name: str
    sector: str
    currency: str
    price: Decimal
    annual_dividend_per_share: Decimal
    dividend_yield: Decimal
    payments_per_year: int = Field(ge=1, le=12)
    compared_cycles: int = Field(ge=2)


class DividendOpportunitiesRead(BaseModel):
    source: str
    source_url: str
    retrieved_at: datetime
    is_delayed: bool
    is_stale: bool
    candidate_count: int = Field(ge=0)
    qualified_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    opportunities: list[DividendOpportunityRead]


class InvestmentFundRead(BaseModel):
    isin: str
    provider_id: str
    name: str
    category: str
    fund_type: str
    fund_company: str
    currency: str
    nav: Decimal
    nav_date: date
    changes: MarketChangesRead
    product_fee: Decimal
    management_fee: Decimal
    risk: int | None = Field(default=None, ge=1, le=7)
    rating: int | None = Field(default=None, ge=1, le=5)
    index_fund: bool


class InvestmentFundDataRead(BaseModel):
    source: str
    source_url: str
    retrieved_at: datetime
    data_date: date | None
    is_delayed: bool
    is_stale: bool
    query: str | None
    result_count: int = Field(ge=0)
    funds: list[InvestmentFundRead]
    unavailable_isins: list[str]
