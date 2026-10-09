import datetime
from typing import Optional, List, Dict, Any
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

@router.post("/live")
def create_live_sale(
    data: SaleCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    tx = create_sale_transaction(db, current_user, data, ip)
    return {
        "success": True,
        "message": f"Venta {tx.doc_type} #{tx.doc_number or tx.id} registrada exitosamente.",
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

@router.get("/live-monitor")
def get_live_monitor(
    date: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from models.system import SystemSetting
    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.date.today()
    txs = db.query(Transaction).filter(
        Transaction.date == target_date,
        Transaction.status != "ANULADO"
    ).order_by(Transaction.id.desc()).all()

    bcv_setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    active_bcv = float(bcv_setting.value) if (bcv_setting and bcv_setting.value) else 36.80

    fac_contado_usd = 0.0
    fac_credito_usd = 0.0
    not_contado_usd = 0.0
    not_credito_usd = 0.0
    abonos_today_usd = 0.0
    returns_today_usd = 0.0
    expenses_today_usd = 0.0

    cash_usd_expected = 0.0
    cash_ves_expected = 0.0
    pos_banesco = 0.0
    pos_bancaribe = 0.0
    pos_bdv = 0.0
    pos_bnc = 0.0
    pago_movil_usd = 0.0
    cashea_usd = 0.0

    recent_stream = []

    for t in txs:
        acc = t.account
        acc_name = acc.name.upper() if acc else ""

        if t.movement_type == "INGRESO":
            if t.doc_type == "FACTURA_FISCAL" or t.subtype == "VENTA_DIARIA":
                if t.is_credit:
                    fac_credito_usd += t.amount_usd
                else:
                    fac_contado_usd += t.amount_usd
            elif t.doc_type == "NOTA_ENTREGA":
                if t.is_credit:
                    not_credito_usd += t.amount_usd
                else:
                    not_contado_usd += t.amount_usd
            elif t.subtype in ["ABONO_CXC", "COBRO_CXC"]:
                abonos_today_usd += t.amount_usd

            if not t.is_credit:
                if "EFECTIVO USD" in acc_name:
                    cash_usd_expected += t.amount_original
                elif "EFECTIVO VES" in acc_name:
                    cash_ves_expected += t.amount_original
                elif "CASHEA" in acc_name:
                    cashea_usd += t.amount_usd
                elif t.pos_terminal:
                    p = t.pos_terminal.upper()
                    if "BANESCO" in p:
                        pos_banesco += t.amount_usd
                    elif "BANCARIBE" in p:
                        pos_bancaribe += t.amount_usd
                    elif "VENEZUELA" in p or "BDV" in p:
                        pos_bdv += t.amount_usd
                    elif "BNC" in p:
                        pos_bnc += t.amount_usd
                    else:
                        pos_banesco += t.amount_usd
                elif "BANCO" in acc_name:
                    pago_movil_usd += t.amount_usd

        elif t.movement_type == "EGRESO":
            if t.subtype in ["DEVOLUCION_VENTA", "DEVOLUCION_CLIENTE"] or t.doc_type == "DEVOLUCION":
                returns_today_usd += t.amount_usd
            elif t.subtype == "GASTO_OPERATIVO":
                expenses_today_usd += t.amount_usd

        recent_stream.append({
            "id": t.id,
            "created_at": t.created_at.strftime("%I:%M %p") if t.created_at else "",
            "doc_type": t.doc_type,
            "doc_number": t.doc_number,
            "client_name": t.client_name,
            "is_credit": t.is_credit,
            "movement_type": t.movement_type,
            "subtype": t.subtype,
            "account_name": t.account.name if t.account else "CxC",
            "amount_original": round(t.amount_original, 2),
            "currency": t.currency,
            "amount_usd": round(t.amount_usd, 2)
        })

    total_sales_today = fac_contado_usd + fac_credito_usd + not_contado_usd + not_credito_usd - returns_today_usd

    return {
        "date": target_date.isoformat(),
        "time": datetime.datetime.now().strftime("%I:%M:%S %p"),
        "bcv_rate": active_bcv,
        "sales": {
            "fac_contado_usd": round(fac_contado_usd, 2),
            "fac_credito_usd": round(fac_credito_usd, 2),
            "not_contado_usd": round(not_contado_usd, 2),
            "not_credito_usd": round(not_credito_usd, 2),
            "abonos_today_usd": round(abonos_today_usd, 2),
            "returns_today_usd": round(returns_today_usd, 2),
            "expenses_today_usd": round(expenses_today_usd, 2),
            "total_sales_today": round(total_sales_today, 2),
            "total_contado_today": round(fac_contado_usd + not_contado_usd + abonos_today_usd - returns_today_usd - expenses_today_usd, 2),
            "total_credito_today": round(fac_credito_usd + not_credito_usd, 2)
        },
        "live_funds_expected": {
            "cash_usd_expected": round(cash_usd_expected, 2),
            "cash_ves_expected": round(cash_ves_expected, 2),
            "pos_banesco": round(pos_banesco, 2),
            "pos_bancaribe": round(pos_bancaribe, 2),
            "pos_bdv": round(pos_bdv, 2),
            "pos_bnc": round(pos_bnc, 2),
            "pos_total": round(pos_banesco + pos_bancaribe + pos_bdv + pos_bnc, 2),
            "pago_movil_usd": round(pago_movil_usd, 2),
            "cashea_usd": round(cashea_usd, 2)
        },
        "recent_stream": recent_stream[:30]
    }

@router.get("/accumulated")
def get_accumulated_sales(
    filter_mode: Optional[str] = Query(default="mes"),
    date: Optional[str] = Query(default=None),
    month: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if filter_mode == "dia" and date:
        try:
            target_d = datetime.date.fromisoformat(date)
            start_date = target_d
            end_date = target_d
            period_label = f"Día {target_d.strftime('%d/%m/%Y')}"
        except Exception:
            start_date = datetime.date.today()
            end_date = start_date
            period_label = f"Día {start_date.strftime('%d/%m/%Y')}"
    elif month:
        try:
            year, m = map(int, month.split("-"))
            start_date = datetime.date(year, m, 1)
            if m == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)
            period_label = f"Mes {month}"
        except Exception:
            start_date = datetime.date.today().replace(day=1)
            end_date = datetime.date.today()
            period_label = f"Mes {start_date.strftime('%Y-%m')}"
    else:
        start_date = datetime.date.today().replace(day=1)
        end_date = datetime.date.today()
        period_label = f"Mes {start_date.strftime('%Y-%m')}"

    txs = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.status != "ANULADO"
    ).order_by(Transaction.id.desc()).all()

    fac_contado_usd = 0.0
    fac_credito_usd = 0.0
    not_contado_usd = 0.0
    not_credito_usd = 0.0
    total_abonos_cxc_usd = 0.0
    total_retentions_iva_usd = 0.0
    total_returns_usd = 0.0
    recent_records = []

    for t in txs:
        if t.movement_type == "INGRESO":
            if t.doc_type == "FACTURA_FISCAL" or t.subtype == "VENTA_DIARIA":
                if t.is_credit:
                    fac_credito_usd += t.amount_usd
                else:
                    fac_contado_usd += t.amount_usd
            elif t.doc_type == "NOTA_ENTREGA":
                if t.is_credit:
                    not_credito_usd += t.amount_usd
                else:
                    not_contado_usd += t.amount_usd
            elif t.subtype in ["COBRO_CXC", "ABONO_CXC"]:
                total_abonos_cxc_usd += t.amount_usd
            
            if t.tax_retention_amount and t.tax_retention_amount > 0:
                total_retentions_iva_usd += t.tax_retention_amount
        elif t.movement_type == "EGRESO":
            if t.subtype in ["DEVOLUCION_VENTA", "DEVOLUCION_CLIENTE"] or t.doc_type == "DEVOLUCION":
                total_returns_usd += t.amount_usd

        recent_records.append({
            "id": t.id,
            "date": t.date.isoformat() if t.date else "",
            "doc_type": t.doc_type or "-",
            "doc_number": t.doc_number or "-",
            "client_name": t.client_name or t.beneficiary or "Cliente Mostrador",
            "is_credit": t.is_credit,
            "condition_label": "A Crédito (CxC)" if t.is_credit else "De Contado",
            "amount_usd": round(t.amount_usd, 2),
            "amount_original": round(t.amount_original, 2),
            "currency": t.currency,
            "tax_retention_amount": round(t.tax_retention_amount or 0.0, 2)
        })

    total_fiscal_iva_usd = fac_contado_usd + fac_credito_usd
    total_notes_despacho_usd = not_contado_usd + not_credito_usd
    total_sales_contado_usd = fac_contado_usd + not_contado_usd
    total_sales_credito_usd = fac_credito_usd + not_credito_usd
    net_sales_usd = total_fiscal_iva_usd + total_notes_despacho_usd - total_returns_usd

    return {
        "filter_mode": filter_mode,
        "date": date or start_date.isoformat(),
        "month": month or start_date.strftime("%Y-%m"),
        "period_label": period_label,
        "period": f"{start_date.isoformat()} al {end_date.isoformat()}",
        "total_fiscal_iva_usd": round(total_fiscal_iva_usd, 2),
        "fac_contado_usd": round(fac_contado_usd, 2),
        "fac_credito_usd": round(fac_credito_usd, 2),
        "total_notes_despacho_usd": round(total_notes_despacho_usd, 2),
        "not_contado_usd": round(not_contado_usd, 2),
        "not_credito_usd": round(not_credito_usd, 2),
        "total_sales_contado_usd": round(total_sales_contado_usd, 2),
        "total_sales_credito_usd": round(total_sales_credito_usd, 2),
        "total_abonos_cxc_usd": round(total_abonos_cxc_usd, 2),
        "total_retentions_iva_usd": round(total_retentions_iva_usd, 2),
        "total_returns_usd": round(total_returns_usd, 2),
        "net_sales_usd": round(net_sales_usd, 2),
        "records": recent_records[:100]
    }
