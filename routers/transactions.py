import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Transaction, TreasuryAccount, SystemSetting, User
from core.security import get_current_user, require_roles
from schemas.transactions import TransactionCreate, TransferCreate

router = APIRouter(prefix="/api/transactions", tags=["Transacciones de Tesorería"])

@router.get("")
def list_transactions(
    date: Optional[datetime.date] = None,
    month: Optional[str] = None,
    movement_type: Optional[str] = None,
    subtype: Optional[str] = None,
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Transaction)

    if date:
        q = q.filter(Transaction.date == date)
    elif month:
        try:
            year, m = map(int, month.split("-"))
            start_date = datetime.date(year, m, 1)
            if m == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)
            q = q.filter(Transaction.date >= start_date, Transaction.date <= end_date)
        except Exception:
            pass

    if movement_type:
        q = q.filter(Transaction.movement_type == movement_type)
    if subtype:
        q = q.filter(Transaction.subtype == subtype)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if status_filter:
        q = q.filter(Transaction.status == status_filter)

    total = q.count()
    txs = q.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(offset).limit(limit).all()

    items = []
    for t in txs:
        items.append({
            "id": t.id,
            "date": t.date.isoformat(),
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
            "movement_type": t.movement_type,
            "subtype": t.subtype,
            "account_id": t.account_id,
            "account_name": t.account.name if t.account else "",
            "destination_account_id": t.destination_account_id,
            "destination_account_name": t.destination_account.name if t.destination_account else None,
            "category_id": t.category_id,
            "category_name": t.category.name if t.category else None,
            "category_code": t.category.code if t.category else None,
            "amount_original": round(t.amount_original, 2),
            "currency": t.currency,
            "exchange_rate": round(t.exchange_rate, 2),
            "amount_usd": round(t.amount_usd, 2),
            "reference_number": t.reference_number,
            "beneficiary": t.beneficiary,
            "description": t.description,
            "status": t.status,
            "created_by": t.creator.full_name if t.creator else "Sistema",
            "verified_by": t.verifier.full_name if t.verifier else None
        })

    return {"total": total, "items": items}

@router.post("")
def create_transaction(
    tx_in: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if tx_in.amount_original <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a cero.")

    # 1. Restricción para cajeras: No pueden hacer cambios de divisas ni traspasos
    if current_user.role == "cajera" and (tx_in.subtype == "CAMBIO_DIVISAS" or tx_in.movement_type in ["TRASPASO", "TRANSFERENCIA"]):
        raise HTTPException(status_code=403, detail="Los usuarios de caja no tienen permiso para registrar cambios de divisas ni traspasos.")

    account = db.query(TreasuryAccount).filter(TreasuryAccount.id == tx_in.account_id).first()
    if not account:
        raise HTTPException(status_code=400, detail="La cuenta de tesorería seleccionada no existe.")

    # 2. Restricción Cashea: Solo para ingresos
    if (getattr(account, 'only_income', False) or 'CASHEA' in account.name.upper()) and tx_in.movement_type == "EGRESO":
        raise HTTPException(status_code=400, detail=f"La cuenta '{account.name}' está configurada exclusivamente para registrar INGRESOS.")

    # Control estricto de duplicados por referencia bancaria (en todas las cuentas)
    if tx_in.reference_number and len(tx_in.reference_number.strip()) > 2 and tx_in.subtype != "VENTA_DIARIA":
        ref = tx_in.reference_number.strip()
        dup = db.query(Transaction).filter(
            Transaction.reference_number.ilike(ref),
            Transaction.status != "ANULADO"
        ).first()
        if dup:
            acc_name = dup.account.name if dup.account else "Desconocida"
            raise HTTPException(
                status_code=400,
                detail=f"¡ALERTA DE PAGO DUPLICADO! La referencia bancaria '{ref}' ya fue registrada el {dup.date} por ${dup.amount_usd:.2f} en '{acc_name}' (Beneficiario: {dup.beneficiary}). Verifique para evitar pagos duplicados."
            )

    # 3. Tasa BCV Oficial Obligatoria (salvo cambio de divisas que es negociado)
    bcv_setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    active_bcv = float(bcv_setting.value) if (bcv_setting and bcv_setting.value) else 827.74

    if tx_in.currency == "VES":
        if tx_in.subtype != "CAMBIO_DIVISAS":
            rate = active_bcv
        else:
            rate = tx_in.exchange_rate if tx_in.exchange_rate > 0 else active_bcv
        calc_usd = round(tx_in.amount_original / rate, 2)
    elif tx_in.currency in ["USD", "USDT"]:
        calc_usd = round(tx_in.amount_original, 2)
        rate = 1.0
    else:
        calc_usd = tx_in.amount_usd or tx_in.amount_original
        rate = tx_in.exchange_rate or 1.0

    if tx_in.subtype == "GASTO_OPERATIVO" and not tx_in.category_id:
        raise HTTPException(status_code=400, detail="Para un gasto operativo debe seleccionar la Partida Presupuestaria correspondiente.")

    # Adaptación para Venta Diaria
    benef = tx_in.beneficiary.strip() if tx_in.beneficiary else ""
    desc = tx_in.description.strip() if tx_in.description else ""
    if tx_in.subtype == "VENTA_DIARIA":
        if not benef:
            benef = "Ventas Mostrador - Tienda Valencia"
        if not desc:
            desc = f"Cierre de ventas del día ({account.name})"

    # Normalizar movement_type si el frontend envió TRANSFERENCIA
    mov_type = "TRASPASO" if tx_in.movement_type == "TRANSFERENCIA" else tx_in.movement_type

    tx = Transaction(
        branch_id=current_user.branch_id,
        date=tx_in.date,
        movement_type=mov_type,
        subtype=tx_in.subtype,
        account_id=account.id,
        destination_account_id=tx_in.destination_account_id,
        category_id=tx_in.category_id,
        amount_original=tx_in.amount_original,
        currency=tx_in.currency,
        exchange_rate=rate,
        amount_usd=calc_usd,
        reference_number=tx_in.reference_number.strip() if tx_in.reference_number else "",
        beneficiary=benef,
        description=desc,
        doc_type=tx_in.doc_type or "FACTURA_FISCAL",
        doc_number=tx_in.doc_number.strip() if tx_in.doc_number else "",
        is_credit=tx_in.is_credit or False,
        credit_status="PENDIENTE" if tx_in.is_credit else "PAGADO",
        tax_retention_amount=tx_in.tax_retention_amount or 0.0,
        tax_retention_proof=tx_in.tax_retention_proof.strip() if tx_in.tax_retention_proof else "",
        pos_terminal=tx_in.pos_terminal.strip() if tx_in.pos_terminal else "",
        pos_lot_number=tx_in.pos_lot_number.strip() if tx_in.pos_lot_number else "",
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return {
        "success": True,
        "message": "Movimiento registrado con éxito",
        "id": tx.id,
        "amount_usd": tx.amount_usd
    }

@router.post("/transfer")
def create_transfer(
    trans_in: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if trans_in.origin_account_id == trans_in.destination_account_id:
        raise HTTPException(status_code=400, detail="La cuenta de origen y destino no pueden ser la misma.")
    if trans_in.amount_origin <= 0 or trans_in.amount_destination <= 0:
        raise HTTPException(status_code=400, detail="Los montos deben ser mayores a cero.")

    acc_orig = db.query(TreasuryAccount).filter(TreasuryAccount.id == trans_in.origin_account_id).first()
    acc_dest = db.query(TreasuryAccount).filter(TreasuryAccount.id == trans_in.destination_account_id).first()
    if not acc_orig or not acc_dest:
        raise HTTPException(status_code=400, detail="Una de las cuentas seleccionadas no existe.")

    rate = trans_in.exchange_rate if trans_in.exchange_rate > 0 else 1.0

    if acc_orig.currency in ["USD", "USDT"]:
        orig_usd = trans_in.amount_origin
    else:
        orig_usd = round(trans_in.amount_origin / rate, 2)

    if acc_dest.currency in ["USD", "USDT"]:
        dest_usd = trans_in.amount_destination
    else:
        dest_usd = round(trans_in.amount_destination / rate, 2)

    # 1. Asiento 1: Egreso de Cuenta Origen
    tx_out = Transaction(
        branch_id=current_user.branch_id,
        date=trans_in.date,
        movement_type="EGRESO",
        subtype="TRASPASO_SALIDA",
        account_id=acc_orig.id,
        destination_account_id=acc_dest.id,
        amount_original=trans_in.amount_origin,
        currency=acc_orig.currency,
        exchange_rate=rate,
        amount_usd=orig_usd,
        reference_number=trans_in.reference_number or "",
        beneficiary=f"Hacia: {acc_dest.name}",
        description=f"Salida por Traspaso/Cambio hacia {acc_dest.name}. {trans_in.description or ''}".strip(),
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx_out)

    # 2. Asiento 2: Ingreso a Cuenta Destino (Partida Doble)
    tx_in = Transaction(
        branch_id=current_user.branch_id,
        date=trans_in.date,
        movement_type="INGRESO",
        subtype="TRASPASO_ENTRADA",
        account_id=acc_dest.id,
        destination_account_id=acc_orig.id,
        amount_original=trans_in.amount_destination,
        currency=acc_dest.currency,
        exchange_rate=rate,
        amount_usd=dest_usd,
        reference_number=trans_in.reference_number or "",
        beneficiary=f"Desde: {acc_orig.name}",
        description=f"Entrada por Traspaso/Cambio desde {acc_orig.name}. {trans_in.description or ''}".strip(),
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx_in)
    db.commit()

    return {
        "success": True,
        "message": f"Traspaso de fondos registrado con éxito: {trans_in.amount_origin} {acc_orig.currency} -> {trans_in.amount_destination} {acc_dest.currency}",
        "out_id": tx_out.id,
        "in_id": tx_in.id
    }

@router.patch("/{id}/verify")
def verify_transaction(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    tx = db.query(Transaction).filter(Transaction.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    tx.status = "VERIFICADO"
    tx.verified_by_id = current_user.id
    db.commit()
    return {"success": True, "message": f"Movimiento #{id} marcado como VERIFICADO"}

@router.delete("/{id}")
def cancel_transaction(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    tx = db.query(Transaction).filter(Transaction.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    tx.status = "ANULADO"
    db.commit()
    return {"success": True, "message": f"Movimiento #{id} ha sido ANULADO"}
