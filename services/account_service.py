from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from models import TreasuryAccount, Transaction, AccountMonthlyBalance

def get_active_accounts(db: Session, include_inactive: bool = False):
    query = db.query(TreasuryAccount)
    if not include_inactive:
        query = query.filter(TreasuryAccount.is_active == True)
    return query.order_by(TreasuryAccount.id.asc()).all()

def toggle_account_status(db: Session, account_id: int) -> TreasuryAccount:
    acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    acc.is_active = not acc.is_active
    db.commit()
    db.refresh(acc)
    return acc

def create_account(db: Session, data) -> TreasuryAccount:
    clean_name = data.name.strip()
    existing = db.query(TreasuryAccount).filter(TreasuryAccount.name.ilike(clean_name)).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.currency = data.currency.upper()
            existing.account_type = data.account_type.upper()
            if data.initial_balance is not None:
                existing.initial_balance = data.initial_balance
            if data.only_income is not None:
                existing.only_income = data.only_income
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=400, detail=f"Ya existe una cuenta activa con el nombre '{data.name}'.")
    acc = TreasuryAccount(
        name=clean_name,
        currency=data.currency.upper(),
        account_type=data.account_type.upper(),
        initial_balance=data.initial_balance,
        only_income=data.only_income,
        is_active=True
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc
