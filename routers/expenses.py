from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Transaction, Supplier, User
from core.security import get_current_user, require_roles
from schemas.expenses import ExpenseCreate, RetentionAddRequest, SupplierCreate
from services.expense_service import create_expense_transaction, add_post_payment_retention

import datetime
from typing import Optional
from sqlalchemy import func

router = APIRouter(prefix="/api/expenses", tags=["Egresos y Proveedores"])

@router.get("")
def list_expenses(
    date: Optional[str] = None,
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(
        Transaction.movement_type == 'EGRESO',
        Transaction.status != 'ANULADO'
    )
    if date:
        try:
            d = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(Transaction.date == d)
        except Exception:
            pass
    elif month:
        query = query.filter(func.to_char(Transaction.date, 'YYYY-MM') == month if db.bind.dialect.name == 'postgresql' else func.strftime('%Y-%m', Transaction.date) == month)
        
    expenses = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    return [{
        "id": e.id,
        "date": str(e.date),
        "beneficiary": e.beneficiary,
        "category_id": e.category_id,
        "category_name": e.category.name if e.category else "General",
        "subtype": e.subtype,
        "amount_usd": e.amount_usd,
        "currency": e.currency,
        "reference_number": e.reference_number,
        "doc_number": e.doc_number,
        "description": e.description,
        "status": e.status,
        "tax_retention_amount": e.tax_retention_amount,
        "tax_retention_proof": e.tax_retention_proof
    } for e in expenses]

@router.post("")
def create_expense(
    data: ExpenseCreate,
    request: Request,
    current_user: User = Depends(require_roles(["administradora", "directivo", "cajera", "cajero"])),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    tx = create_expense_transaction(db, current_user, data, ip)
    return {
        "id": tx.id,
        "date": str(tx.date),
        "beneficiary": tx.beneficiary,
        "amount_usd": tx.amount_usd,
        "tax_retention_amount": tx.tax_retention_amount,
        "tax_retention_proof": tx.tax_retention_proof,
        "status": tx.status
    }

@router.post("/{transaction_id}/retention")
def add_retention(
    transaction_id: int,
    data: RetentionAddRequest,
    request: Request,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    tx = add_post_payment_retention(db, current_user, transaction_id, data, ip)
    return {
        "id": tx.id,
        "tax_retention_amount": tx.tax_retention_amount,
        "tax_retention_proof": tx.tax_retention_proof,
        "message": "Comprobante de retención SENIAT registrado con éxito."
    }

@router.get("/suppliers")
def get_suppliers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name.asc()).all()
    return [{"id": s.id, "name": s.name, "rif": s.rif, "phone": s.phone} for s in suppliers]

@router.post("/suppliers")
def create_supplier(
    data: SupplierCreate,
    current_user: User = Depends(require_roles(["administradora", "directivo", "cajera", "cajero"])),
    db: Session = Depends(get_db)
):
    existing = db.query(Supplier).filter(Supplier.name == data.name.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un proveedor con ese nombre.")
    s = Supplier(
        name=data.name.strip(),
        rif=data.rif.strip() if data.rif else None,
        phone=data.phone.strip() if data.phone else None,
        bank_details=data.bank_details.strip() if data.bank_details else '',
        is_active=True
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "name": s.name, "rif": s.rif}
