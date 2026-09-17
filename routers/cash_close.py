import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from database import get_db
from models import DailyCashClose, User
from core.security import get_current_user, require_roles
from schemas.cash_close import CashCloseCreate
from core.audit import record_audit

router = APIRouter(prefix="/api/cash-closes", tags=["Cierres de Caja"])

@router.get("")
def list_cash_closes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    closes = db.query(DailyCashClose).order_by(DailyCashClose.date.desc()).all()
    return [{
        "id": c.id,
        "date": str(c.date),
        "cajero_name": c.cajero_name,
        "status": c.status,
        "total_collected_real_usd": c.total_collected_real_usd,
        "total_expected_usd": c.total_expected_usd,
        "difference_usd": c.difference_usd
    } for c in closes]

@router.post("")
def create_cash_close(
    data: CashCloseCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    close_date = datetime.datetime.strptime(data.date, "%Y-%m-%d").date()
    existing = db.query(DailyCashClose).filter(DailyCashClose.date == close_date).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe un cierre de caja registrado para la fecha {data.date}.")

    total_real = (data.cash_usd_physical + data.pos_total_usd + data.bank_transfers_usd +
                  data.cashea_usd + data.retentions_iva_usd + data.retentions_islr_usd)

    close_obj = DailyCashClose(
        branch_id=current_user.branch_id,
        date=close_date,
        cajero_name=current_user.full_name,
        status=data.status,
        profit_sales_total_usd=data.profit_sales_total_usd,
        sales_fiscal_iva_usd=data.sales_fiscal_iva_usd,
        sales_notes_credit_usd=data.sales_notes_credit_usd,
        sales_notes_collected_usd=data.sales_notes_collected_usd,
        returns_total_usd=data.returns_total_usd,
        cash_usd_physical=data.cash_usd_physical,
        cash_ves_physical=data.cash_ves_physical,
        pos_total_usd=data.pos_total_usd,
        bank_transfers_usd=data.bank_transfers_usd,
        cashea_usd=data.cashea_usd,
        retentions_iva_usd=data.retentions_iva_usd,
        retentions_islr_usd=data.retentions_islr_usd,
        expenses_caja_usd=data.expenses_caja_usd,
        total_collected_real_usd=total_real,
        total_expected_usd=data.total_expected_usd,
        difference_usd=data.difference_usd,
        arqueo_usd_json=data.arqueo_usd_json or '{}',
        arqueo_ves_json=data.arqueo_ves_json or '{}',
        pos_details_json=data.pos_details_json or '{}',
        notes=data.notes or ''
    )
    db.add(close_obj)
    db.flush()
    ip = request.client.host if request.client else ""
    record_audit(db, current_user, 'CREATE_CASH_CLOSE', 'DailyCashClose', str(close_obj.id), {
        'date': str(close_date),
        'difference_usd': data.difference_usd,
        'status': data.status
    }, ip)
    db.commit()
    db.refresh(close_obj)
    return {"id": close_obj.id, "date": str(close_obj.date), "status": close_obj.status}
