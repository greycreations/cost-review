from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Expense, Provider
from app.schemas import CategoryRead, ExpenseRead, HealthRead, ProviderRead

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/health", response_model=HealthRead, tags=["system"])
def health(db: DatabaseSession) -> HealthRead:
    db.execute(text("SELECT 1"))
    return HealthRead(status="ok", database="reachable")


@router.get("/providers", response_model=list[ProviderRead], tags=["providers"])
def list_providers(db: DatabaseSession) -> list[Provider]:
    return list(db.scalars(select(Provider).order_by(Provider.name, Provider.provider_id)))


@router.get("/categories", response_model=list[CategoryRead], tags=["categories"])
def list_categories(db: DatabaseSession) -> list[Category]:
    statement = select(Category).order_by(
        Category.sort_order,
        Category.name,
        Category.category_id,
    )
    return list(db.scalars(statement))


@router.get("/expenses", response_model=list[ExpenseRead], tags=["expenses"])
def list_expenses(db: DatabaseSession) -> list[Expense]:
    return list(db.scalars(select(Expense).order_by(Expense.name, Expense.expense_id)))
