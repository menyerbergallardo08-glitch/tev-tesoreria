from typing import Optional, List, Dict, Any
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from database import get_db
from models import DailyCashClose, User, Transaction
from core.security import get_current_user, require_roles
from schemas.cash_close import CashCloseCreate
from core.audit import record_audit

router = APIRouter(prefix="/api/cash-closes", tags=["Cierres de Caja"])
cash_close_legacy_router = APIRouter(prefix="/api/cash-close", tags=["Cierre de Caja Legacy"])

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

@cash_close_legacy_router.get("/summary")
def get_cash_close_summary(
    date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.date.today()
    txs = db.query(Transaction).filter(
        Transaction.date == target_date,
        Transaction.status != "ANULADO"
    ).all()

    existing_close = db.query(DailyCashClose).filter(DailyCashClose.date == target_date).first()

    sales_fiscal_iva_usd = 0.0
    sales_notes_credit_usd = 0.0
    sales_notes_collected_usd = 0.0
    returns_total_usd = 0.0
    expenses_caja_usd = 0.0

    cash_usd_in = 0.0
    cash_usd_out = 0.0
    cash_ves_in = 0.0
    cash_ves_out = 0.0

    pos_breakdown = {"Banesco": 0.0, "Bancaribe": 0.0, "BDV": 0.0, "BNC": 0.0, "Otros": 0.0}
    pos_total_usd = 0.0

    bank_transfers_usd = 0.0
    cashea_usd = 0.0
    retentions_iva_usd = 0.0
    retentions_islr_usd = 0.0

    for t in txs:
        acc = t.account
        acc_name = acc.name.upper() if acc else ""

        if t.movement_type == "INGRESO":
            if t.doc_type == "FACTURA_FISCAL" or t.subtype == "VENTA_DIARIA":
                sales_fiscal_iva_usd += t.amount_usd
            elif t.doc_type == "NOTA_ENTREGA":
                if t.is_credit:
                    sales_notes_credit_usd += t.amount_usd
                else:
                    sales_notes_collected_usd += t.amount_usd
            elif t.subtype in ["COBRO_CXC", "ABONO_CXC"]:
                sales_notes_collected_usd += t.amount_usd

            if t.tax_retention_amount and t.tax_retention_amount > 0:
                retentions_iva_usd += t.tax_retention_amount

            if "EFECTIVO USD" in acc_name:
                cash_usd_in += t.amount_original
            elif "EFECTIVO VES" in acc_name:
                cash_ves_in += t.amount_original
            elif "CASHEA" in acc_name:
                cashea_usd += t.amount_usd
            elif "BANCO" in acc_name or "PUNTO" in acc_name or "POS" in acc_name:
                if t.pos_terminal:
                    p_term = t.pos_terminal.upper()
                    if "BANESCO" in p_term:
                        pos_breakdown["Banesco"] += t.amount_usd
                    elif "BANCARIBE" in p_term:
                        pos_breakdown["Bancaribe"] += t.amount_usd
                    elif "VENEZUELA" in p_term or "BDV" in p_term:
                        pos_breakdown["BDV"] += t.amount_usd
                    elif "BNC" in p_term:
                        pos_breakdown["BNC"] += t.amount_usd
                    else:
                        pos_breakdown["Otros"] += t.amount_usd
                    pos_total_usd += t.amount_usd
                else:
                    bank_transfers_usd += t.amount_usd
            else:
                bank_transfers_usd += t.amount_usd

        elif t.movement_type == "EGRESO":
            if t.subtype in ["DEVOLUCION_VENTA", "DEVOLUCION_CLIENTE"] or t.doc_type == "DEVOLUCION":
                returns_total_usd += t.amount_usd
            elif t.subtype == "GASTO_OPERATIVO":
                expenses_caja_usd += t.amount_usd

            if "EFECTIVO USD" in acc_name:
                cash_usd_out += t.amount_original
            elif "EFECTIVO VES" in acc_name:
                cash_ves_out += t.amount_original

    net_sales_usd = round(sales_fiscal_iva_usd + sales_notes_credit_usd - returns_total_usd, 2)
    total_collected_real_usd = round(cash_usd_in + (cash_ves_in / 36.80) + pos_total_usd + bank_transfers_usd + cashea_usd, 2)

    return {
        "date": target_date.isoformat(),
        "is_closed": bool(existing_close),
        "existing_close": {
            "id": existing_close.id,
            "status": existing_close.status,
            "cajero_name": existing_close.cajero_name,
            "verified_by": existing_close.verified_by,
            "created_at": existing_close.created_at.strftime("%Y-%m-%d %H:%M:%S") if existing_close.created_at else "",
            "profit_sales_total_usd": existing_close.profit_sales_total_usd,
            "net_sales_usd": existing_close.net_sales_usd,
            "difference_usd": existing_close.difference_usd,
            "notes": existing_close.notes
        } if existing_close else None,
        "sales_summary": {
            "fiscal_iva_usd": round(sales_fiscal_iva_usd, 2),
            "notes_credit_usd": round(sales_notes_credit_usd, 2),
            "notes_collected_usd": round(sales_notes_collected_usd, 2),
            "returns_total_usd": round(returns_total_usd, 2),
            "net_sales_usd": net_sales_usd
        },
        "collections_summary": {
            "cash_usd_in": round(cash_usd_in, 2),
            "cash_usd_out": round(cash_usd_out, 2),
            "cash_usd_net": round(cash_usd_in - cash_usd_out, 2),
            "cash_ves_in": round(cash_ves_in, 2),
            "cash_ves_out": round(cash_ves_out, 2),
            "cash_ves_net": round(cash_ves_in - cash_ves_out, 2),
            "pos_total_usd": round(pos_total_usd, 2),
            "pos_breakdown": pos_breakdown,
            "bank_transfers_usd": round(bank_transfers_usd, 2),
            "cashea_usd": round(cashea_usd, 2),
            "retentions_iva_usd": round(retentions_iva_usd, 2),
            "retentions_islr_usd": round(retentions_islr_usd, 2),
            "expenses_caja_usd": round(expenses_caja_usd, 2),
            "total_collected_real_usd": total_collected_real_usd
        },
        "transactions_count": len(txs)
    }

@cash_close_legacy_router.post("")
def save_daily_cash_close_legacy(
    data: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    date_val = data.get("date")
    close_date = datetime.datetime.strptime(date_val, "%Y-%m-%d").date() if date_val else datetime.date.today()
    existing = db.query(DailyCashClose).filter(DailyCashClose.date == close_date).first()
    
    if existing:
        for k, v in data.items():
            if hasattr(existing, k) and k not in ['id', 'created_at']:
                if k == 'date':
                    setattr(existing, k, close_date)
                else:
                    setattr(existing, k, v)
        existing.cajero_name = current_user.full_name
        db.commit()
        db.refresh(existing)
        return {"success": True, "message": f"Cuadre de caja del {close_date} actualizado.", "id": existing.id}
    else:
        new_close = DailyCashClose(
            branch_id=current_user.branch_id,
            date=close_date,
            cajero_name=current_user.full_name,
            verified_by=data.get("verified_by", "Administración"),
            status=data.get("status", "CUADRADO"),
            profit_sales_total_usd=float(data.get("profit_sales_total_usd", 0.0) or 0.0),
            sales_fiscal_iva_usd=float(data.get("sales_fiscal_iva_usd", 0.0) or 0.0),
            sales_notes_credit_usd=float(data.get("sales_notes_credit_usd", 0.0) or 0.0),
            sales_notes_collected_usd=float(data.get("sales_notes_collected_usd", 0.0) or 0.0),
            returns_total_usd=float(data.get("returns_total_usd", 0.0) or 0.0),
            net_sales_usd=float(data.get("net_sales_usd", 0.0) or 0.0),
            cash_usd_physical=float(data.get("cash_usd_physical", 0.0) or 0.0),
            cash_ves_physical=float(data.get("cash_ves_physical", 0.0) or 0.0),
            pos_total_usd=float(data.get("pos_total_usd", 0.0) or 0.0),
            bank_transfers_usd=float(data.get("bank_transfers_usd", 0.0) or 0.0),
            cashea_usd=float(data.get("cashea_usd", 0.0) or 0.0),
            retentions_iva_usd=float(data.get("retentions_iva_usd", 0.0) or 0.0),
            retentions_islr_usd=float(data.get("retentions_islr_usd", 0.0) or 0.0),
            expenses_caja_usd=float(data.get("expenses_caja_usd", 0.0) or 0.0),
            total_collected_real_usd=float(data.get("total_collected_real_usd", 0.0) or 0.0),
            total_expected_usd=float(data.get("total_expected_usd", 0.0) or 0.0),
            difference_usd=float(data.get("difference_usd", 0.0) or 0.0),
            notes=data.get("notes", "") or ""
        )
        db.add(new_close)
        db.commit()
        db.refresh(new_close)
        return {"success": True, "message": f"Cuadre de caja del {close_date} cerrado y registrado con éxito.", "id": new_close.id}

@cash_close_legacy_router.get("/history")
def list_cash_close_history(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    closes = db.query(DailyCashClose).order_by(DailyCashClose.date.desc()).limit(limit).all()
    res = []
    for c in closes:
        res.append({
            "id": c.id,
            "date": c.date.isoformat(),
            "cajero_name": c.cajero_name,
            "status": c.status,
            "profit_sales_total_usd": round(c.profit_sales_total_usd, 2),
            "net_sales_usd": round(c.net_sales_usd, 2),
            "difference_usd": round(c.difference_usd, 2)
        })
    return res
