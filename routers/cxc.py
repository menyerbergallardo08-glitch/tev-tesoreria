from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Transaction, User
from core.security import get_current_user, require_roles
from schemas.cxc import HistoricalDebtCreate, CxCPaymentCreate
from services.cxc_service import create_historical_debt, process_cxc_payment

router = APIRouter(prefix="/api/cxc", tags=["Cuentas por Cobrar"])

@router.get("/debts")
def list_pending_debts(
    status: str = Query(default="ALL"), # 'ALL', 'PENDING', 'PAID'
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(
        Transaction.is_credit == True,
        Transaction.status != 'ANULADO'
    )
    if status == 'PENDING':
        query = query.filter(Transaction.credit_balance_pending_usd > 0)
    elif status == 'PAID':
        query = query.filter(Transaction.credit_balance_pending_usd == 0)
    
    debts = query.order_by(Transaction.date.desc()).all()
    return [{
        "id": d.id,
        "date": str(d.date),
        "doc_type": d.doc_type,
        "doc_number": d.doc_number,
        "client_name": d.client_name,
        "client_rif": d.client_rif,
        "credit_original_amount_usd": d.credit_original_amount_usd,
        "credit_balance_pending_usd": d.credit_balance_pending_usd,
        "credit_status": d.credit_status,
        "description": d.description
    } for d in debts]

@router.post("/historical-debt")
def register_historical_debt(
    data: HistoricalDebtCreate,
    request: Request,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    tx = create_historical_debt(db, current_user, data, ip)
    return {
        "id": tx.id,
        "client_name": tx.client_name,
        "doc_type": tx.doc_type,
        "doc_number": tx.doc_number,
        "credit_original_amount_usd": tx.credit_original_amount_usd,
        "credit_balance_pending_usd": tx.credit_balance_pending_usd,
        "message": "Deuda histórica cargada exitosamente sin alterar ventas de hoy."
    }

@router.post("/payments")
def collect_cxc(
    data: CxCPaymentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    tx = process_cxc_payment(db, current_user, data, ip)
    return {
        "id": tx.id,
        "amount_usd": tx.amount_usd,
        "parent_transaction_id": tx.parent_transaction_id,
        "doc_number": tx.doc_number,
        "message": "Abono / Cobro registrado exitosamente."
    }
