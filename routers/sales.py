import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Transaction, User
from core.security import get_current_user, require_roles
from schemas.sales import SaleCreate, SaleVoidRequest
from services.sales_service import create_sale_transaction
from core.audit import record_audit

router = APIRouter(prefix="/api/sales", tags=["Ventas y Caja"])

@router.post("")
def create_sale(
    data: SaleCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    tx = create_sale_transaction(db, current_user, data, ip)
    return {
        "id": tx.id,
        "date": str(tx.date),
        "doc_type": tx.doc_type,
        "doc_number": tx.doc_number,
        "client_name": tx.client_name,
        "amount_usd": tx.amount_usd,
        "is_credit": tx.is_credit,
        "credit_status": tx.credit_status,
        "credit_balance_pending_usd": tx.credit_balance_pending_usd,
        "status": tx.status
    }

@router.post("/void")
def void_sale(
    data: SaleVoidRequest,
    request: Request,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    tx = db.query(Transaction).filter(Transaction.id == data.transaction_id).with_for_update().first()
    if not tx:
        raise HTTPException(status_code=404, detail="Venta no encontrada.")
    if tx.status == 'ANULADO':
        raise HTTPException(status_code=400, detail="Esta venta ya fue anulada previamente.")

    tx.status = 'ANULADO'
    tx.description = f"[ANULADO por {current_user.username}: {data.reason}] {tx.description or ''}".strip()
    
    ip = request.client.host if request.client else ""
    record_audit(db, current_user, 'VOID_SALE', 'Transaction', str(tx.id), {'reason': data.reason}, ip)
    db.commit()
    return {"message": f"Transacción #{tx.id} anulada exitosamente."}

@router.get("/summary-today")
def get_sales_summary_today(
    date: str = Query(default=str(datetime.date.today())),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    sales = db.query(Transaction).filter(
        Transaction.date == target_date,
        Transaction.movement_type == 'INGRESO',
        Transaction.subtype.in_(['VENTA_DIARIA', 'ABONO_CXC']),
        Transaction.status != 'ANULADO'
    ).all()

    total_cash_usd = sum(s.amount_usd for s in sales if s.account and s.account.currency == 'USD' and s.account.account_type == 'EFECTIVO')
    total_cash_ves_usd = sum(s.amount_usd for s in sales if s.account and s.account.currency == 'VES' and s.account.account_type == 'EFECTIVO')
    total_pos_usd = sum(s.amount_usd for s in sales if s.pos_terminal or (s.account and s.account.account_type == 'BANCO' and 'Punto' in (s.description or '')))
    total_collected = sum(s.amount_usd for s in sales)
    
    return {
        "date": str(target_date),
        "total_sales_count": len(sales),
        "total_collected_usd": round(total_collected, 2),
        "cash_usd": round(total_cash_usd, 2),
        "cash_ves_usd": round(total_cash_ves_usd, 2),
        "pos_usd": round(total_pos_usd, 2)
    }
