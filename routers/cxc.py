from typing import Optional, List, Dict, Any
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, engine
from models import Transaction, User, TreasuryAccount
from models.system import SystemSetting
from core.security import get_current_user, require_roles
from schemas.cxc import HistoricalDebtCreate, CxCPaymentCreate
from services.cxc_service import create_historical_debt, process_cxc_payment
from core.audit import record_audit

router = APIRouter(prefix="/api/cxc", tags=["Cuentas por Cobrar"])
receivables_router = APIRouter(prefix="/api/receivables", tags=["Receivables CxC"])

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
        "seller_code": d.seller_code,
        "seller_name": d.seller_name,
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

@receivables_router.get("")
def list_receivables(
    status_filter: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Transaction).filter(
        Transaction.is_credit == True,
        Transaction.status != "ANULADO"
    )

    if status_filter and status_filter != 'TODOS':
        q = q.filter(Transaction.credit_status == status_filter)
    elif not status_filter:
        q = q.filter(Transaction.credit_status.in_(["PENDIENTE", "PARCIALMENTE_PAGADO"]))

    if search:
        s = f"%{search.strip()}%"
        q = q.filter(
            (Transaction.client_name.ilike(s)) |
            (Transaction.doc_number.ilike(s)) |
            (Transaction.client_rif.ilike(s))
        )

    credits = q.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    res = []
    for c in credits:
        abonos = db.query(Transaction).filter(
            Transaction.parent_transaction_id == c.id,
            Transaction.status != "ANULADO"
        ).order_by(Transaction.date.asc()).all()

        total_credit = c.credit_original_amount_usd if (c.credit_original_amount_usd and c.credit_original_amount_usd > 0) else c.amount_usd
        total_abonado = sum(a.amount_usd for a in abonos)
        if c.credit_balance_pending_usd is not None:
            pending = max(0.0, c.credit_balance_pending_usd - total_abonado)
        else:
            pending = max(0.0, total_credit - total_abonado)

        res.append({
            "id": c.id,
            "date": c.date.isoformat() if c.date else "",
            "doc_type": c.doc_type,
            "doc_number": c.doc_number,
            "client_name": c.client_name or c.beneficiary,
            "client_rif": c.client_rif or "-",
            "original_amount_usd": round(total_credit, 2),
            "total_abonado_usd": round(total_abonado, 2),
            "pending_balance_usd": round(pending, 2),
            "credit_status": "PAGADO" if pending <= 0.01 else ("PARCIALMENTE_PAGADO" if (total_credit - pending) > 0.01 else "PENDIENTE"),
            "abonos_count": len(abonos),
            "abonos_history": [
                {
                    "id": a.id,
                    "date": a.date.isoformat() if a.date else "",
                    "amount_usd": round(a.amount_usd, 2),
                    "amount_orig": round(a.amount_original, 2),
                    "currency": a.currency,
                    "account_name": a.account.name if a.account else "",
                    "reference": a.reference_number
                } for a in abonos
            ]
        })
    return res

@receivables_router.post("/{credit_id}/abono")
def create_abono(
    credit_id: int,
    data: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Transaction).filter(Transaction.id == credit_id, Transaction.is_credit == True)
    if engine.dialect.name != 'sqlite':
        parent = query.with_for_update().first()
    else:
        parent = query.first()
    if not parent:
        raise HTTPException(status_code=404, detail="Cuenta por cobrar no encontrada.")

    is_retention = bool(data.get("is_retention"))
    retention_proof = (data.get("tax_retention_proof") or "").strip()
    
    account_id = data.get("account_id")
    if is_retention:
        # Buscar o crear cuenta contable de Retenciones SENIAT Recibidas de Clientes
        ret_acc = db.query(TreasuryAccount).filter(TreasuryAccount.account_type == 'RETENCION_CLIENTE').first()
        if not ret_acc:
            ret_acc = TreasuryAccount(
                name='Retenciones SENIAT Recibidas de Clientes',
                currency='USD',
                account_type='RETENCION_CLIENTE',
                initial_balance=0.0,
                is_active=True
            )
            db.add(ret_acc)
            db.flush()
        account = ret_acc
    else:
        account = db.query(TreasuryAccount).filter(TreasuryAccount.id == account_id).first()
        if not account:
            raise HTTPException(status_code=400, detail="Cuenta de tesorería no encontrada.")

    bcv_setting = db.query(SystemSetting).filter(SystemSetting.key.in_(['tasa_bcv', 'bcv_rate'])).order_by(SystemSetting.id.desc()).first()
    active_bcv = float(bcv_setting.value) if (bcv_setting and bcv_setting.value and float(bcv_setting.value) > 100) else 881.0664

    amount_original = float(data.get("amount_original", 0.0) or 0.0)
    currency = data.get("currency", "USD")
    custom_rate = float(data.get("exchange_rate", 0.0) or 0.0)
    
    if currency == "VES":
        rate = custom_rate if custom_rate > 1.0 else active_bcv
        calc_usd = round(amount_original / rate, 2)
    else:
        rate = 1.0
        calc_usd = round(amount_original, 2)

    date_str = data.get("date")
    abono_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.date.today()

    sub_label = "RETENCION_CLIENTE_CXC" if is_retention else "ABONO_CXC"
    desc = data.get("description", "") or (f"Retención SENIAT aplicada por {parent.client_name} (Comp: {retention_proof})" if is_retention else f"Abono a {parent.doc_type} #{parent.doc_number}")

    tx = Transaction(
        branch_id=current_user.branch_id,
        date=abono_date,
        movement_type="INGRESO",
        subtype=sub_label,
        account_id=account.id,
        amount_original=amount_original,
        currency=currency,
        exchange_rate=rate,
        amount_usd=calc_usd,
        doc_type="RETENCION_SENIAT" if is_retention else "ABONO_CXC",
        doc_number=retention_proof if (is_retention and retention_proof) else f"ABONO-{parent.doc_number or parent.id}",
        client_name=parent.client_name,
        client_rif=parent.client_rif,
        beneficiary=parent.client_name,
        parent_transaction_id=parent.id,
        reference_number=retention_proof if is_retention else (data.get("reference_number", "")),
        tax_retention_amount=calc_usd if is_retention else 0.0,
        tax_retention_proof=retention_proof if is_retention else "",
        description=desc,
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx)
    db.flush()

    total_ab = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.parent_transaction_id == parent.id,
        Transaction.status != "ANULADO"
    ).scalar() or 0.0

    orig_total = parent.credit_original_amount_usd if (parent.credit_original_amount_usd and parent.credit_original_amount_usd > 0) else parent.amount_usd
    rem = max(0.0, float(orig_total) - float(total_ab))
    parent.credit_balance_pending_usd = round(rem, 2)
    parent.credit_status = "PAGADO" if rem <= 0.01 else "PARCIALMENTE_PAGADO"

    ip = request.client.host if request.client else ""
    record_audit(
        db,
        current_user,
        "ABONO_CXC",
        "Transaction",
        str(tx.id),
        {
            "parent_id": parent.id,
            "parent_doc": parent.doc_number,
            "abono_usd": calc_usd,
            "remaining_usd": rem,
            "client": parent.client_name
        },
        ip
    )
    db.commit()
    db.refresh(tx)

    return {
        "success": True,
        "message": f"{'Retención SENIAT' if is_retention else 'Abono'} de ${calc_usd:.2f} registrado con éxito. Saldo restante: ${rem:.2f}",
        "abono_id": tx.id,
        "is_retention": is_retention,
        "remaining_balance_usd": round(rem, 2),
        "status": parent.credit_status
    }
