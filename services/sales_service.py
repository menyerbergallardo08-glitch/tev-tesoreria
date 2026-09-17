import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Transaction, TreasuryAccount, User
from core.audit import record_audit

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
