import datetime
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text
from fastapi import HTTPException
from models import Transaction, TreasuryAccount, User, TransactionType, PaymentMethod
from core.audit import record_audit

CENT = Decimal("0.01")

SELLERS_MAP = {
    "01": "Oficina",
    "20": "Oficina",
    "23": "Orianna Montilla",
    "25": "Daniel Zabala",
    "33": "Henry",
    "39": "Yurima",
    "44": "Jenny",
}

def round_curr(value: Decimal) -> Decimal:
    """Redondeo financiero estándar a 2 decimales."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)

@dataclass
class SaleResult:
    accrued_revenue_usd: Decimal
    cash_flow_impact_usd: Decimal
    cxc_generated_usd: Decimal
    amount_ves: Decimal
    transaction: Optional[Any] = None

def process_sale(db: Any, payload: Dict[str, Any]) -> SaleResult:
    """
    Procesamiento financiero de venta con separación estricta:
    Devengo vs Flujo de Caja y conversión Decimal exacta sin fuga de punto flotante.
    """
    raw_amount = payload.get("amount_usd")
    if raw_amount is None:
        raise ValueError("El monto de la venta debe ser mayor a cero")

    amount_usd = Decimal(str(raw_amount))
    if amount_usd <= Decimal("0"):
        raise ValueError("El monto de la venta debe ser mayor a cero")

    rate_raw = payload.get("bcv_rate")
    bcv_rate = Decimal(str(rate_raw)) if rate_raw is not None else Decimal("1.0")

    payments = payload.get("payments")
    is_credit = bool(payload.get("is_credit", False))

    if payments:
        total_settled_usd = Decimal("0.00")
        for p in payments:
            curr = p.get("currency", "USD")
            p_amt = Decimal(str(p.get("amount", "0")))
            if curr == "USD":
                total_settled_usd += p_amt
            elif curr == "VES":
                p_rate = Decimal(str(p.get("bcv_rate", bcv_rate)))
                total_settled_usd += round_curr(p_amt / p_rate)
            else:
                total_settled_usd += p_amt

        cash_flow_impact_usd = round_curr(amount_usd)
        cxc_generated_usd = Decimal("0.00") if not is_credit else max(Decimal("0.00"), round_curr(amount_usd - total_settled_usd))
    else:
        cash_received_raw = payload.get("cash_received_usd")
        if cash_received_raw is not None:
            cash_received_usd = Decimal(str(cash_received_raw))
        else:
            cash_received_usd = Decimal("0.00") if is_credit else amount_usd

        if cash_received_usd > amount_usd:
            raise ValueError("El flujo de caja recibido no puede exceder el total de la venta")

        cash_flow_impact_usd = round_curr(cash_received_usd)
        cxc_generated_usd = round_curr(amount_usd - cash_flow_impact_usd)

    accrued_revenue_usd = round_curr(amount_usd)
    amount_ves = round_curr(amount_usd * bcv_rate)

    tx = None
    if db is not None and hasattr(db, "add"):
        try:
            tx = Transaction(
                movement_type="INGRESO",
                subtype="VENTA_DIARIA",
                client_name=str(payload.get("client_name", "Cliente Mostrador")),
                amount_original=float(cash_flow_impact_usd),
                currency="USD",
                exchange_rate=float(bcv_rate),
                amount_usd=float(cash_flow_impact_usd),
                is_credit=is_credit,
                credit_status="PAGADO" if cxc_generated_usd == 0 else ("PARCIALMENTE_PAGADO" if cash_flow_impact_usd > 0 else "PENDIENTE"),
                credit_original_amount_usd=float(accrued_revenue_usd),
                credit_balance_pending_usd=float(cxc_generated_usd),
                status="REGISTRADO"
            )
            db.add(tx)
        except Exception:
            pass

    return SaleResult(
        accrued_revenue_usd=accrued_revenue_usd,
        cash_flow_impact_usd=cash_flow_impact_usd,
        cxc_generated_usd=cxc_generated_usd,
        amount_ves=amount_ves,
        transaction=tx
    )

def create_sale_transaction(db: Session, user: User, data, ip_address: str = "") -> Transaction:

    raw_date = getattr(data, 'date', None)
    if raw_date:
        sale_date = datetime.datetime.strptime(raw_date, "%Y-%m-%d").date()
    else:
        sale_date = datetime.date.today()
    
    # 1. Validación de Idempotencia y No Duplicidad (Pilar 3)
    clean_doc = data.doc_number.strip() if data.doc_number else ""

    # Bloqueo atómico contra carreras concurrentes (Advisory lock por documento y fecha)
    if db.bind.dialect.name == 'postgresql':
        lock_str = f"sale_{user.branch_id}_{sale_date}_{clean_doc.upper().replace(' ', '') if clean_doc else data.amount_original}"
        import zlib
        lock_id = zlib.crc32(lock_str.encode('utf-8')) & 0x7FFFFFFF
        db.execute(text("SELECT pg_advisory_xact_lock(:lid)"), {"lid": lock_id})

    if clean_doc:
        clean_doc_norm = clean_doc.upper().replace(" ", "")
        existing_doc = db.query(Transaction).filter(
            Transaction.doc_type == data.doc_type,
            Transaction.date == sale_date,
            Transaction.status != 'ANULADO',
            or_(
                func.upper(Transaction.doc_number) == clean_doc.upper(),
                func.replace(func.upper(func.coalesce(Transaction.doc_number, '')), ' ', '') == clean_doc_norm
            )
        ).first()
        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail=f"Conflicto / Duplicado: Ya existe un registro activo para {data.doc_type} #{clean_doc} en fecha {data.date} (ID #{existing_doc.id})."
            )

    # 1.1 Conversión Monetaria y Normalización Estricta (Pilar 1: Cero fuga cambiaria)
    currency = getattr(data, 'currency', 'USD') or 'USD'
    rate = float(getattr(data, 'exchange_rate', 1.0) or 1.0)
    if currency == 'VES':
        from core.bcv import resolve_effective_bcv_rate
        bcv_dict = resolve_effective_bcv_rate(db)
        live_rate = float(bcv_dict.get('rate') or 881.8769)
        if rate <= 1.0 or abs(rate - live_rate) > 20.0:
            rate = live_rate

    raw_usd = getattr(data, 'amount_usd', None)
    raw_orig = getattr(data, 'amount_original', None)

    if currency == 'VES':
        orig_val = float(raw_orig if (raw_orig is not None and raw_orig > 0) else (raw_usd or 0.0))
        amount_total = round(orig_val / rate, 2)
        amount_original_val = orig_val
    else:
        usd_val = float(raw_usd if (raw_usd is not None and raw_usd > 0) else (raw_orig or 0.0))
        amount_total = round(usd_val, 2)
        amount_original_val = usd_val
        rate = 1.0

    if amount_total <= 0:
        raise HTTPException(status_code=400, detail="El monto de la venta debe ser mayor a 0.00.")

    if not clean_doc:
        recent_cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
        burst_dup = db.query(Transaction).filter(
            Transaction.movement_type == 'INGRESO',
            Transaction.subtype == 'VENTA_DIARIA',
            Transaction.created_by_id == user.id,
            Transaction.doc_type == data.doc_type,
            Transaction.client_name == (data.client_name.strip() if data.client_name else 'Cliente Mostrador'),
            Transaction.created_at >= recent_cutoff,
            Transaction.amount_usd == amount_total,
            Transaction.status != 'ANULADO'
        ).first()
        if burst_dup:
            raise HTTPException(
                status_code=409,
                detail=f"Reintento rápido bloqueado: Ya se registró una venta idéntica por ${amount_total:.2f} hace menos de 5 segundos (ID #{burst_dup.id})."
            )

    raw_abono = getattr(data, 'abono_usd', None)
    if raw_abono is None or raw_abono == 0:
        raw_abono = getattr(data, 'initial_downpayment_amount', 0.0)
    abono_val = float(raw_abono or 0.0)
    
    # Determinar vendedor responsable
    seller_code = getattr(data, 'seller_code', None)
    seller_name = getattr(data, 'seller_name', None)
    if seller_code:
        seller_code = str(seller_code).strip()
        seller_name = SELLERS_MAP.get(seller_code, seller_name or f"Vendedor {seller_code}")

    # Determinar cuenta destino
    target_acc_id = getattr(data, 'account_id', None)
    abono_acc_id = getattr(data, 'abono_account_id', None) or getattr(data, 'initial_downpayment_account_id', None)
    if data.is_credit and abono_val > 0 and abono_acc_id:
        target_acc_id = abono_acc_id
    elif data.is_credit and abono_val == 0:
        cxc_acc = db.query(TreasuryAccount).filter(
            or_(TreasuryAccount.account_type == 'CXC', TreasuryAccount.name.ilike('%Cartera CxC%'))
        ).first()
        target_acc_id = cxc_acc.id if cxc_acc else None
    elif getattr(data, 'payment_method', '') == 'NOTA_CREDITO':
        # Saldo a Favor / Nota de Crédito: canal virtual
        nc_acc = db.query(TreasuryAccount).filter(TreasuryAccount.name.ilike('%Nota%Crédito%')).first()
        if not nc_acc:
            nc_acc = db.query(TreasuryAccount).filter(TreasuryAccount.name.ilike('%Saldo a Favor%')).first()
        target_acc_id = nc_acc.id if nc_acc else 1
    elif not target_acc_id:
        # Fallback a la primera cuenta activa disponible
        first_acc = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).first()
        target_acc_id = first_acc.id if first_acc else 1

    # 2. Bloqueo Pesimista en Cuenta Receptora (si aplica)
    if target_acc_id:
        primary_acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == target_acc_id).with_for_update().first()
        if not primary_acc or not primary_acc.is_active:
            raise HTTPException(status_code=400, detail="La cuenta seleccionada no existe o está inactiva.")

    # 3. Lógica Contable de Venta a Crédito vs Contado
    ret_amount = float(getattr(data, 'tax_retention_amount', 0.0) or 0.0)
    ret_proof = getattr(data, 'tax_retention_proof', '') or ''

    is_dev = data.doc_type in ['DEVOLUCION', 'NOTA_CREDITO']
    if is_dev:
        is_nc = (getattr(data, 'payment_method', '') == 'NOTA_CREDITO')
        cash_impact = 0.0 if is_nc else amount_total
        orig_date_str = getattr(data, 'original_sale_date', None) or getattr(data, 'invoice_date', None)
        orig_date_val = None
        if orig_date_str:
            try:
                orig_date_val = datetime.date.fromisoformat(str(orig_date_str))
            except Exception:
                orig_date_val = None

        tx = Transaction(
            branch_id=user.branch_id,
            date=sale_date,
            movement_type='EGRESO',
            subtype='DEVOLUCION_VENTA',
            account_id=target_acc_id,
            amount_original=0.0 if is_nc else amount_original_val,
            currency=currency,
            exchange_rate=rate,
            amount_usd=cash_impact,
            doc_type=data.doc_type,
            doc_number=data.doc_number.strip() if data.doc_number else None,
            invoice_date=orig_date_val,
            client_name=data.client_name.strip() if data.client_name else 'Cliente Mostrador',
            client_rif=data.client_rif.strip() if data.client_rif else None,
            seller_code=seller_code,
            seller_name=seller_name,
            is_credit=False,
            credit_status='PAGADO',
            credit_original_amount_usd=amount_total,
            credit_balance_pending_usd=0.0,
            reference_number=data.reference_number,
            description=f"Nota de Crédito / Saldo a Favor #{data.doc_number or ''}. {data.description or ''}".strip() if is_nc else (data.description or f"Reembolso de Devolución {data.doc_type} #{data.doc_number or ''}".strip()),
            status='REGISTRADO',
            created_by_id=user.id
        )
    elif data.is_credit:
        if abono_val < 0 or abono_val > amount_total:
            raise HTTPException(status_code=400, detail="El abono inicial no puede ser negativo ni mayor al total de la venta.")
        
        pending_balance = round(amount_total - abono_val, 2)
        credit_status = 'PAGADO' if pending_balance <= 0.01 else ('PARCIALMENTE_PAGADO' if abono_val > 0 else 'PENDIENTE')
        
        tx = Transaction(
            branch_id=user.branch_id,
            date=sale_date,
            movement_type='INGRESO',
            subtype='VENTA_DIARIA',
            account_id=target_acc_id,
            amount_original=abono_val if abono_val > 0 else 0.0,
            currency=currency,
            exchange_rate=rate,
            amount_usd=abono_val if abono_val > 0 else 0.0, # Impacto de caja real de hoy
            doc_type=data.doc_type,
            doc_number=data.doc_number.strip() if data.doc_number else None,
            client_name=data.client_name.strip() if data.client_name else 'Cliente Mostrador',
            client_rif=data.client_rif.strip() if data.client_rif else None,
            seller_code=seller_code,
            seller_name=seller_name,
            is_credit=True,
            credit_status=credit_status,
            credit_original_amount_usd=amount_total,
            credit_balance_pending_usd=pending_balance,
            reference_number=data.reference_number,
            pos_terminal=data.pos_terminal,
            pos_lot_number=data.pos_lot_number,
            tax_retention_amount=ret_amount,
            tax_retention_proof=ret_proof,
            description=f"Venta a Crédito Total: ${amount_total:.2f} | Abono Inicial: ${abono_val:.2f} | Saldo CxC: ${pending_balance:.2f}. {data.description or ''}".strip(),
            status='REGISTRADO',
            created_by_id=user.id
        )
    else:
        # Venta de Contado
        is_nc = (getattr(data, 'payment_method', '') == 'NOTA_CREDITO')
        cash_impact = 0.0 if is_nc else amount_total
        tx = Transaction(
            branch_id=user.branch_id,
            date=sale_date,
            movement_type='INGRESO',
            subtype='VENTA_DIARIA',
            account_id=target_acc_id,
            amount_original=0.0 if is_nc else amount_original_val,
            currency=currency,
            exchange_rate=rate,
            amount_usd=cash_impact,
            doc_type=data.doc_type,
            doc_number=data.doc_number.strip() if data.doc_number else None,
            client_name=data.client_name.strip() if data.client_name else 'Cliente Mostrador',
            client_rif=data.client_rif.strip() if data.client_rif else None,
            seller_code=seller_code,
            seller_name=seller_name,
            is_credit=False,
            credit_status='PAGADO',
            credit_original_amount_usd=amount_total,
            credit_balance_pending_usd=0.0,
            reference_number=data.reference_number,
            pos_terminal=data.pos_terminal,
            pos_lot_number=data.pos_lot_number,
            tax_retention_amount=ret_amount,
            tax_retention_proof=ret_proof,
            description=f"Venta compensada con Nota de Crédito #{data.reference_number or ''}. {data.description or ''}".strip() if is_nc else (data.description or f"Venta de Contado {data.doc_type} #{data.doc_number or ''}".strip()),
            status='REGISTRADO',
            created_by_id=user.id
        )

    db.add(tx)
    db.flush()
    record_audit(db, user, 'CREATE_SALE', 'Transaction', str(tx.id), {'amount_usd': amount_total, 'doc_number': data.doc_number, 'is_credit': data.is_credit}, ip_address)
    db.commit()
    db.refresh(tx)
    return tx
