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

@router.put("/{account_id}")
def update_account(
    account_id: int,
    data: AccountUpdate,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    if data.name is not None and data.name.strip():
        acc.name = data.name.strip()
    if data.account_type is not None and data.account_type.strip():
        acc.account_type = data.account_type.strip().upper()
    if data.initial_balance is not None:
        acc.initial_balance = float(data.initial_balance)
    if data.only_income is not None:
        acc.only_income = data.only_income
    if data.is_active is not None:
        acc.is_active = data.is_active

    db.commit()
    db.refresh(acc)
    return {
        "id": acc.id,
        "name": acc.name,
        "currency": acc.currency,
        "account_type": acc.account_type,
        "initial_balance": acc.initial_balance,
        "is_active": acc.is_active
    }

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
