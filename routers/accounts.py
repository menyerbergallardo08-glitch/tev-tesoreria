from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import TreasuryAccount, User
from core.security import get_current_user, require_roles
from schemas.accounts import AccountCreate, AccountUpdate, MonthlyBalanceCreate
from services.account_service import get_active_accounts, toggle_account_status, create_account

router = APIRouter(prefix="/api/accounts", tags=["Cajas y Bancos"])

@router.get("")
def list_accounts(
    all: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    accounts = get_active_accounts(db, include_inactive=all)
    return [{
        "id": a.id,
        "name": a.name,
        "currency": a.currency,
        "account_type": a.account_type,
        "initial_balance": a.initial_balance,
        "only_income": a.only_income,
        "is_active": a.is_active
    } for a in accounts]

@router.post("")
def add_account(
    data: AccountCreate,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    acc = create_account(db, data)
    return {"id": acc.id, "name": acc.name, "currency": acc.currency, "is_active": acc.is_active}

@router.post("/{account_id}/toggle-status")
def toggle_status(
    account_id: int,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    acc = toggle_account_status(db, account_id)
    return {
        "id": acc.id,
        "name": acc.name,
        "is_active": acc.is_active,
        "message": f"Cuenta '{acc.name}' {'activada' if acc.is_active else 'inhabilitada'} correctamente."
    }
