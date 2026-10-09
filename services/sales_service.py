import datetime
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Transaction, TreasuryAccount, User, TransactionType, PaymentMethod
from core.audit import record_audit

CENT = Decimal("0.01")

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

    sale_date = datetime.datetime.strptime(data.date, "%Y-%m-%d").date()
    
    # 1. Validación de Idempotencia y No Duplicidad (Pilar 3)
    if data.doc_number:
        clean_doc = data.doc_number.strip()
        existing_doc = db.query(Transaction).filter(
            Transaction.doc_type == data.doc_type,
            Transaction.doc_number == clean_doc,
            Transaction.date == sale_date,
            Transaction.status != 'ANULADO'
        ).first()
        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail=f"Conflicto / Duplicado: Ya existe un registro activo para {data.doc_type} #{clean_doc} en fecha {data.date} (ID #{existing_doc.id})."
            )

    amount_total = float(data.amount_usd)
    abono_val = float(data.abono_usd) if data.abono_usd else 0.0
    
    # Determinar cuenta destino
    target_acc_id = data.account_id
    if data.is_credit and abono_val > 0 and data.abono_account_id:
        target_acc_id = data.abono_account_id
    elif not target_acc_id:
        # Fallback a la primera cuenta activa disponible
        first_acc = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).first()
        target_acc_id = first_acc.id if first_acc else 1

    # 2. Bloqueo Pesimista en Cuenta Receptora
    primary_acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == target_acc_id).with_for_update().first()
    if not primary_acc or not primary_acc.is_active:
        raise HTTPException(status_code=400, detail="La cuenta seleccionada no existe o está inactiva.")

    # 3. Lógica Contable de Venta a Crédito vs Contado
    if data.is_credit:
        if abono_val < 0 or abono_val > amount_total:
            raise HTTPException(status_code=400, detail="El abono inicial no puede ser negativo ni mayor al total de la venta.")
        
        pending_balance = round(amount_total - abono_val, 2)
        credit_status = 'PAGADO' if pending_balance == 0 else ('PARCIALMENTE_PAGADO' if abono_val > 0 else 'PENDIENTE')
        
        tx = Transaction(
            branch_id=user.branch_id,
            date=sale_date,
            movement_type='INGRESO',
            subtype='VENTA_DIARIA',
            account_id=target_acc_id,
            amount_original=abono_val if abono_val > 0 else 0.0,
            currency='USD',
            exchange_rate=data.exchange_rate or 1.0,
            amount_usd=abono_val if abono_val > 0 else 0.0, # Solo entra a caja el abono real!
            doc_type=data.doc_type,
            doc_number=data.doc_number.strip() if data.doc_number else None,
            client_name=data.client_name.strip() if data.client_name else 'Cliente Mostrador',
            client_rif=data.client_rif.strip() if data.client_rif else None,
            is_credit=True,
            credit_status=credit_status,
            credit_original_amount_usd=amount_total,
            credit_balance_pending_usd=pending_balance,
            reference_number=data.reference_number,
            pos_terminal=data.pos_terminal,
            pos_lot_number=data.pos_lot_number,
            description=f"Venta a Crédito Total: ${amount_total:.2f} | Abono Inicial: ${abono_val:.2f} | Saldo CxC: ${pending_balance:.2f}. {data.description or ''}".strip(),
            status='REGISTRADO',
            created_by_id=user.id
        )
    else:
        # Venta de Contado
        tx = Transaction(
            branch_id=user.branch_id,
            date=sale_date,
            movement_type='INGRESO',
            subtype='VENTA_DIARIA',
            account_id=target_acc_id,
            amount_original=data.amount_usd,
            currency='USD',
            exchange_rate=data.exchange_rate or 1.0,
            amount_usd=amount_total,
            doc_type=data.doc_type,
            doc_number=data.doc_number.strip() if data.doc_number else None,
            client_name=data.client_name.strip() if data.client_name else 'Cliente Mostrador',
            client_rif=data.client_rif.strip() if data.client_rif else None,
            is_credit=False,
            credit_status='PAGADO',
            credit_original_amount_usd=amount_total,
            credit_balance_pending_usd=0.0,
            reference_number=data.reference_number,
            pos_terminal=data.pos_terminal,
            pos_lot_number=data.pos_lot_number,
            description=data.description or f"Venta de Contado {data.doc_type} #{data.doc_number or ''}".strip(),
            status='REGISTRADO',
            created_by_id=user.id
        )

    db.add(tx)
    db.flush()
    record_audit(db, user, 'CREATE_SALE', 'Transaction', str(tx.id), {'amount_usd': amount_total, 'doc_number': data.doc_number, 'is_credit': data.is_credit}, ip_address)
    db.commit()
    db.refresh(tx)
    return tx
