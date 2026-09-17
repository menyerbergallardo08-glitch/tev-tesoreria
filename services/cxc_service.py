import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Transaction, TreasuryAccount, User
from core.audit import record_audit

def create_historical_debt(db: Session, user: User, data, ip_address: str = "") -> Transaction:
    emission_date = datetime.datetime.strptime(data.emission_date, "%Y-%m-%d").date()
    
    # 1. Verificar que no exista ya la misma nota histórica
    existing = db.query(Transaction).filter(
        Transaction.doc_type == data.doc_type,
        Transaction.doc_number == data.doc_number.strip(),
        Transaction.status != 'ANULADO'
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe un registro con {data.doc_type} #{data.doc_number}.")

    # Cuenta por defecto para registrar la cuenta de orden histórica (no altera balance de caja)
    default_acc = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).first()
    if not default_acc:
        raise HTTPException(status_code=400, detail="No hay cuentas de tesorería activas.")

    amount_val = float(data.amount_usd)
    tx = Transaction(
        branch_id=user.branch_id,
        date=emission_date,
        movement_type='INGRESO',
        subtype='COBRO_CXC',
        account_id=default_acc.id,
        amount_original=0.0, # Cero en caja física!
        currency='USD',
        exchange_rate=1.0,
        amount_usd=0.0, # Cero en flujo de caja de hoy!
        doc_type=data.doc_type,
        doc_number=data.doc_number.strip(),
        client_name=data.client_name.strip(),
        client_rif=data.client_rif.strip() if data.client_rif else None,
        is_credit=True,
        credit_status='PENDIENTE',
        credit_original_amount_usd=amount_val,
        credit_balance_pending_usd=amount_val,
        description=f"Saldo Inicial / Deuda Histórica anterior al sistema. {data.notes or ''}".strip(),
        status='REGISTRADO',
        created_by_id=user.id
    )
    db.add(tx)
    db.flush()
    record_audit(db, user, 'CREATE_HISTORICAL_DEBT', 'Transaction', str(tx.id), {'amount_usd': amount_val, 'doc_number': data.doc_number}, ip_address)
    db.commit()
    db.refresh(tx)
    return tx

def process_cxc_payment(db: Session, user: User, data, ip_address: str = "") -> Transaction:
    parent_tx = db.query(Transaction).filter(Transaction.id == data.transaction_id).with_for_update().first()
    if not parent_tx or parent_tx.status == 'ANULADO':
        raise HTTPException(status_code=404, detail="Deuda o nota de entrega no encontrada.")

    if not parent_tx.is_credit or parent_tx.credit_balance_pending_usd <= 0:
        raise HTTPException(status_code=400, detail="Esta cuenta no tiene saldo pendiente por cobrar.")

    payment_amount = float(data.amount_usd)
    if payment_amount <= 0 or payment_amount > parent_tx.credit_balance_pending_usd + 0.01:
        raise HTTPException(status_code=400, detail=f"El monto del abono (${payment_amount:.2f}) no puede exceder el saldo pendiente (${parent_tx.credit_balance_pending_usd:.2f}).")

    target_acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == data.account_id).with_for_update().first()
    if not target_acc or not target_acc.is_active:
        raise HTTPException(status_code=400, detail="La cuenta receptora no existe o está inactiva.")

    today_date = datetime.date.today()
    new_balance = round(parent_tx.credit_balance_pending_usd - payment_amount, 2)
    parent_tx.credit_balance_pending_usd = new_balance
    parent_tx.credit_status = 'PAGADO' if new_balance == 0 else 'PARCIALMENTE_PAGADO'

    # Registrar el ingreso real a caja de hoy
    abono_tx = Transaction(
        branch_id=user.branch_id,
        date=today_date,
        movement_type='INGRESO',
        subtype='ABONO_CXC',
        account_id=target_acc.id,
        amount_original=payment_amount,
        currency='USD',
        exchange_rate=data.exchange_rate or 1.0,
        amount_usd=payment_amount,
        doc_type='ABONO_CXC',
        doc_number=f"ABONO-{parent_tx.doc_number or parent_tx.id}",
        client_name=parent_tx.client_name,
        client_rif=parent_tx.client_rif,
        parent_transaction_id=parent_tx.id,
        reference_number=data.reference_number,
        description=f"Cobro / Abono a {parent_tx.doc_type} #{parent_tx.doc_number}. Saldo restante: ${new_balance:.2f}. {data.description or ''}".strip(),
        status='REGISTRADO',
        created_by_id=user.id
    )
    db.add(abono_tx)
    db.flush()
    record_audit(db, user, 'PROCESS_CXC_PAYMENT', 'Transaction', str(abono_tx.id), {
        'parent_id': parent_tx.id,
        'abono_usd': payment_amount,
        'saldo_restante': new_balance
    }, ip_address)
    db.commit()
    db.refresh(abono_tx)
    return abono_tx
