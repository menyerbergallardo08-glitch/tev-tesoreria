from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import BudgetCategory, Transaction, User
from core.security import get_current_user

router = APIRouter(prefix="/api/categories", tags=["Categorías y Presupuesto"])

@router.get("")
def list_categories(
    month: str = '2026-09',
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    categories = db.query(BudgetCategory).filter(BudgetCategory.is_active == True).order_by(BudgetCategory.code.asc()).all()
    results = []
    for cat in categories:
        spent = db.query(func.sum(Transaction.amount_usd)).filter(
            Transaction.category_id == cat.id,
            Transaction.movement_type == 'EGRESO',
            Transaction.status != 'ANULADO',
            func.to_char(Transaction.date, 'YYYY-MM') == month if db.bind.dialect.name == 'postgresql' else func.strftime('%Y-%m', Transaction.date) == month
        ).scalar() or 0.0
        results.append({
            "id": cat.id,
            "code": cat.code,
            "name": cat.name,
            "monthly_budget_usd": cat.monthly_budget_usd,
            "spent_usd": round(spent, 2),
            "remaining_usd": round(cat.monthly_budget_usd - spent, 2)
        })
    return results
