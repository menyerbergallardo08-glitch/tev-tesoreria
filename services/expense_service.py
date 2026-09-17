import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Transaction, TreasuryAccount, BudgetCategory, User
from core.seniat import validate_and_format_retention_proof
from core.audit import record_audit

def create_expense_transaction(db: Session, user: User, data, ip_address: str = "") -> Transaction:
    expense_date = datetime.datetime.strptime(data.date, "%Y-%m-%d").date()

    # Validación de Retención SENIAT
    formatted_proof = None
    if data.tax_retention_proof or (data.tax_retention_amount and data.tax_retention_amount > 0):
        formatted_proof = validate_and_format_retention_proof(data.tax_retention_proof, data.tax_retention_amount)

    # Bloqueo Pesimista en Cuenta de Egreso
    account = db.query(TreasuryAccount).filter(TreasuryAccount.id == data.account_id).with_for_update().first()
    if not account or not account.is_active:
        raise HTTPException(status_code=400, detail="La cuenta de egreso seleccionada no existe o está inactiva.")

    # Idempotencia por referencia / factura de proveedor
    if data.reference_number:
        clean_ref = data.reference_number.strip()
        existing = db.query(Transaction).filter(
            Transaction.movement_type == 'EGRESO',
            Transaction.reference_number == clean_ref,
            Transaction.date == expense_date,
            Transaction.status != 'ANULADO'
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Conflicto: Ya existe un egreso registrado con la referencia #{clean_ref} en fecha {data.date} (ID #{existing.id})."
            )

    tx = Transaction(
        branch_id=user.branch_id,
        date=expense_date,
        movement_type='EGRESO',
        subtype=data.subtype,
        account_id=data.account_id,
        category_id=data.category_id,
        amount_original=data.amount_original or data.amount_usd,
        currency=data.currency.upper(),
        exchange_rate=data.exchange_rate or 1.0,
        amount_usd=data.amount_usd,
        beneficiary=data.beneficiary.strip(),
        reference_number=data.reference_number.strip() if data.reference_number else None,
        doc_number=data.doc_number.strip() if data.doc_number else None,
        description=data.description or f"Egreso: {data.beneficiary}",
        tax_retention_amount=data.tax_retention_amount or 0.0,
        tax_retention_proof=formatted_proof,
        status='REGISTRADO',
        created_by_id=user.id
    )
    db.add(tx)
    db.flush()
    record_audit(db, user, 'CREATE_EXPENSE', 'Transaction', str(tx.id), {'amount_usd': data.amount_usd, 'beneficiary': data.beneficiary}, ip_address)
    db.commit()
    db.refresh(tx)
    return tx

def add_post_payment_retention(db: Session, user: User, transaction_id: int, data, ip_address: str = "") -> Transaction:
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).with_for_update().first()
    if not tx or tx.status == 'ANULADO':
        raise HTTPException(status_code=404, detail="Transacción no encontrada o anulada.")
    
    formatted_proof = validate_and_format_retention_proof(data.tax_retention_proof, data.tax_retention_amount)
    tx.tax_retention_amount = data.tax_retention_amount
    tx.tax_retention_proof = formatted_proof
    
    record_audit(db, user, 'ADD_POST_RETENTION', 'Transaction', str(tx.id), {
        'tax_retention_amount': data.tax_retention_amount,
        'tax_retention_proof': formatted_proof
    }, ip_address)
    
    db.commit()
    db.refresh(tx)
    return tx
