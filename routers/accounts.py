from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import TreasuryAccount, AccountMonthlyBalance, User
from core.security import get_current_user, require_roles
from schemas.accounts import AccountCreate, AccountUpdate, MonthlyBalanceCreate, MonthlyBalancesBulkPayload
from services.account_service import get_active_accounts, toggle_account_status, create_account

router = APIRouter(prefix="/api/accounts", tags=["Cajas y Bancos"])

@router.get("/monthly-balances")
def get_monthly_balances(
    month: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    accounts = get_active_accounts(db, include_inactive=False)
    res = []
    for a in accounts:
        bal = db.query(AccountMonthlyBalance).filter(
            AccountMonthlyBalance.account_id == a.id,
            AccountMonthlyBalance.month == month
        ).first()
        init_val = bal.initial_balance if bal else (a.initial_balance or 0.0)
        res.append({
            "account_id": a.id,
            "name": a.name,
            "currency": a.currency,
            "initial_balance": round(float(init_val), 2)
        })
    return {"month": month, "balances": res}

@router.post("/monthly-balances")
def set_monthly_balances(
    payload: MonthlyBalancesBulkPayload,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    for item in payload.balances:
        bal = db.query(AccountMonthlyBalance).filter(
            AccountMonthlyBalance.account_id == item.account_id,
            AccountMonthlyBalance.month == payload.month
        ).first()
        if not bal:
            bal = AccountMonthlyBalance(
                account_id=item.account_id,
                month=payload.month,
                initial_balance=float(item.initial_balance)
            )
            db.add(bal)
        else:
            bal.initial_balance = float(item.initial_balance)
    db.commit()
    return {"status": "success", "message": f"Saldos iniciales para {payload.month} guardados correctamente."}

@router.get("")
def list_accounts(
    all: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from models import Transaction
    from sqlalchemy import func
    accounts = get_active_accounts(db, include_inactive=all)
    res = []
    for a in accounts:
        ingresos = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == a.id,
            Transaction.movement_type == "INGRESO",
            Transaction.status != "ANULADO"
        ).scalar() or 0.0

        egresos = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == a.id,
            Transaction.movement_type == "EGRESO",
            Transaction.status != "ANULADO"
        ).scalar() or 0.0

        calc_balance = (a.initial_balance or 0.0) + float(ingresos) - float(egresos)

        res.append({
            "id": a.id,
            "name": a.name,
            "currency": a.currency,
            "account_type": a.account_type,
            "initial_balance": a.initial_balance,
            "current_balance": round(calc_balance, 2),
            "only_income": a.only_income,
            "is_active": a.is_active
        })
    return res

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

@router.delete("/{account_id}")
def delete_account(
    account_id: int,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    from models import Transaction
    acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    tx_count = db.query(Transaction).filter(
        (Transaction.account_id == account_id) | (Transaction.destination_account_id == account_id)
    ).count()

    if tx_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar la cuenta '{acc.name}' porque posee {tx_count} transacciones asociadas. Puede inhabilitarla en su lugar."
        )

    db.delete(acc)
    db.commit()
    return {"status": "success", "message": f"Cuenta '{acc.name}' eliminada exitosamente."}

