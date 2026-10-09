from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from database import get_db
from models import BudgetCategory, Transaction, User
from core.security import get_current_user, require_roles
from schemas.categories import CategoryCreate, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["Categorías y Presupuesto"])

@router.get("")
def list_categories(
    month: str = '2026-09',
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(BudgetCategory)
    if not include_inactive:
        query = query.filter(BudgetCategory.is_active == True)
    categories = query.order_by(BudgetCategory.code.asc()).all()

    results = []
    for cat in categories:
        spent = db.query(func.sum(Transaction.amount_usd)).filter(
            Transaction.category_id == cat.id,
            Transaction.movement_type == 'EGRESO',
            Transaction.status != 'ANULADO',
            func.to_char(Transaction.date, 'YYYY-MM') == month if db.bind.dialect.name == 'postgresql' else func.strftime('%Y-%m', Transaction.date) == month
        ).scalar() or 0.0

        monthly_budget = cat.monthly_budget_usd or 0.0
        remaining = round(monthly_budget - spent, 2)
        pct = round((spent / monthly_budget * 100), 1) if monthly_budget > 0 else 0.0
        status = 'ALERTA' if spent > monthly_budget and monthly_budget > 0 else 'APTO'

        results.append({
            "id": cat.id,
            "code": cat.code,
            "name": cat.name,
            "monthly_budget_usd": monthly_budget,
            "spent_usd": round(spent, 2),
            "remaining_usd": remaining,
            "percentage_spent": pct,
            "status": status,
            "is_active": cat.is_active
        })
    return results

@router.post("")
def create_category(
    data: CategoryCreate,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    existing = db.query(BudgetCategory).filter(BudgetCategory.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe una partida con el código {data.code}.")

    cat = BudgetCategory(
        code=data.code,
        name=data.name.strip(),
        monthly_budget_usd=data.monthly_budget_usd,
        is_active=True
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {
        "id": cat.id,
        "code": cat.code,
        "name": cat.name,
        "monthly_budget_usd": cat.monthly_budget_usd,
        "is_active": cat.is_active
    }

@router.put("/{category_id}")
def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    cat = db.query(BudgetCategory).filter(BudgetCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Partida presupuestaria no encontrada.")

    if data.name is not None:
        cat.name = data.name.strip()
    if data.monthly_budget_usd is not None:
        cat.monthly_budget_usd = data.monthly_budget_usd
    if data.is_active is not None:
        cat.is_active = data.is_active

    db.commit()
    db.refresh(cat)
    return {
        "id": cat.id,
        "code": cat.code,
        "name": cat.name,
        "monthly_budget_usd": cat.monthly_budget_usd,
        "is_active": cat.is_active
    }

