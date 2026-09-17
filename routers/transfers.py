import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Transaction, TreasuryAccount, User
from core.security import require_roles
from core.audit import record_audit

router = APIRouter(prefix="/api/transfers", tags=["Traspasos y Cambio de Divisas"])

class TransferRequest(BaseModel):
    date: str
    origin_account_id: int
    destination_account_id: int
    amount_usd: float
    description: str = ''

@router.post("")
def create_transfer(
    data: TransferRequest,
    request: Request,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    if data.origin_account_id == data.destination_account_id:
        raise HTTPException(status_code=400, detail="La cuenta de origen y destino deben ser diferentes.")

    origin = db.query(TreasuryAccount).filter(TreasuryAccount.id == data.origin_account_id).with_for_update().first()
    dest = db.query(TreasuryAccount).filter(TreasuryAccount.id == data.destination_account_id).with_for_update().first()

    if not origin or not dest or not origin.is_active or not dest.is_active:
        raise HTTPException(status_code=400, detail="Una o ambas cuentas no existen o están inactivas.")

    t_date = datetime.datetime.strptime(data.date, "%Y-%m-%d").date()
    tx = Transaction(
        branch_id=current_user.branch_id,
        date=t_date,
        movement_type='TRASPASO',
        subtype='TRASPASO_CUENTAS',
        account_id=origin.id,
        destination_account_id=dest.id,
        amount_original=data.amount_usd,
        currency='USD',
        exchange_rate=1.0,
        amount_usd=data.amount_usd,
        description=data.description or f"Traspaso de {origin.name} a {dest.name}",
        status='REGISTRADO',
        created_by_id=current_user.id
    )
    db.add(tx)
    db.flush()
    ip = request.client.host if request.client else ""
    record_audit(db, current_user, 'CREATE_TRANSFER', 'Transaction', str(tx.id), {'amount_usd': data.amount_usd}, ip)
    db.commit()
    return {"id": tx.id, "message": "Traspaso registrado exitosamente."}
