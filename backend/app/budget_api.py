from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.budget_schemas import (
    AnalysisGroupCreate,
    AnalysisGroupRead,
    AnalysisGroupUpdate,
    BudgetCreate,
    BudgetOutcomeRead,
    BudgetRead,
    BudgetTransactionRead,
    BudgetTrendRead,
    BudgetUpdate,
)
from app.budget_services import (
    analysis_group_values,
    budget_outcome,
    budget_transactions,
    budget_trend,
    budget_values,
    create_analysis_group,
    create_budget,
    get_analysis_group,
    get_budget,
    list_analysis_groups,
    list_budgets,
    set_analysis_group_archived,
    set_budget_archived,
    update_analysis_group,
    update_budget,
)
from app.dependencies import Auth, CsrfAuth, DatabaseSession
from app.ledger_schemas import AnalysisPerspective

router = APIRouter(tags=["analysis-and-budgets"])


@router.get("/analysis-groups", response_model=list[AnalysisGroupRead])
def get_analysis_groups(
    _: Auth, db: DatabaseSession, include_archived: bool = False
) -> list[dict[str, object]]:
    return list_analysis_groups(db, include_archived)


@router.post("/analysis-groups", response_model=AnalysisGroupRead, status_code=201)
def post_analysis_group(
    payload: AnalysisGroupCreate, _: CsrfAuth, db: DatabaseSession
) -> dict[str, object]:
    return analysis_group_values(create_analysis_group(db, payload))


@router.patch("/analysis-groups/{group_id}", response_model=AnalysisGroupRead)
def patch_analysis_group(
    group_id: int,
    payload: AnalysisGroupUpdate,
    _: CsrfAuth,
    db: DatabaseSession,
) -> dict[str, object]:
    return analysis_group_values(
        update_analysis_group(db, get_analysis_group(db, group_id), payload)
    )


@router.post("/analysis-groups/{group_id}/archive", response_model=AnalysisGroupRead)
def archive_analysis_group(group_id: int, _: CsrfAuth, db: DatabaseSession) -> dict[str, object]:
    return analysis_group_values(
        set_analysis_group_archived(db, get_analysis_group(db, group_id), True)
    )


@router.post("/analysis-groups/{group_id}/restore", response_model=AnalysisGroupRead)
def restore_analysis_group(group_id: int, _: CsrfAuth, db: DatabaseSession) -> dict[str, object]:
    return analysis_group_values(
        set_analysis_group_archived(db, get_analysis_group(db, group_id), False)
    )


@router.get("/budgets", response_model=list[BudgetRead])
def get_budgets(
    _: Auth, db: DatabaseSession, include_archived: bool = False
) -> list[dict[str, object]]:
    return list_budgets(db, include_archived)


@router.post("/budgets", response_model=BudgetRead, status_code=201)
def post_budget(payload: BudgetCreate, auth: CsrfAuth, db: DatabaseSession) -> dict[str, object]:
    return budget_values(create_budget(db, payload, auth.user.settings.base_currency))


@router.patch("/budgets/{budget_id}", response_model=BudgetRead)
def patch_budget(
    budget_id: int,
    payload: BudgetUpdate,
    auth: CsrfAuth,
    db: DatabaseSession,
) -> dict[str, object]:
    return budget_values(
        update_budget(
            db,
            get_budget(db, budget_id),
            payload,
            auth.user.settings.base_currency,
        )
    )


@router.post("/budgets/{budget_id}/archive", response_model=BudgetRead)
def archive_budget(budget_id: int, _: CsrfAuth, db: DatabaseSession) -> dict[str, object]:
    return budget_values(set_budget_archived(db, get_budget(db, budget_id), True))


@router.post("/budgets/{budget_id}/restore", response_model=BudgetRead)
def restore_budget(budget_id: int, _: CsrfAuth, db: DatabaseSession) -> dict[str, object]:
    return budget_values(set_budget_archived(db, get_budget(db, budget_id), False))


@router.get("/budgets/{budget_id}/outcome", response_model=BudgetOutcomeRead)
def get_budget_outcome(
    budget_id: int,
    date_from: date,
    date_to: date,
    auth: Auth,
    db: DatabaseSession,
    perspective: AnalysisPerspective = AnalysisPerspective.TOTAL,
) -> dict[str, object]:
    return budget_outcome(
        db,
        get_budget(db, budget_id),
        date_from,
        date_to,
        auth.user.settings.base_currency,
        perspective.value,
    )


@router.get("/budgets/{budget_id}/transactions", response_model=list[BudgetTransactionRead])
def get_budget_transactions(
    budget_id: int,
    date_from: date,
    date_to: date,
    auth: Auth,
    db: DatabaseSession,
    perspective: AnalysisPerspective = AnalysisPerspective.TOTAL,
) -> list[dict[str, object]]:
    return budget_transactions(
        db,
        get_budget(db, budget_id),
        date_from,
        date_to,
        auth.user.settings.base_currency,
        perspective.value,
    )


@router.get("/budgets/{budget_id}/trend", response_model=BudgetTrendRead)
def get_budget_trend(
    budget_id: int,
    through: date,
    auth: Auth,
    db: DatabaseSession,
    periods: int = Query(default=6, ge=1, le=24),
    perspective: AnalysisPerspective = AnalysisPerspective.TOTAL,
) -> dict[str, object]:
    return budget_trend(
        db,
        get_budget(db, budget_id),
        through,
        periods,
        auth.user.settings.base_currency,
        perspective.value,
    )
