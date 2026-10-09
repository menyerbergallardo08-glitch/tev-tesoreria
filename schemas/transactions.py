import datetime
from pydantic import BaseModel
from typing import Optional

class TransactionCreate(BaseModel):
    date: datetime.date
    movement_type: str  # 'INGRESO', 'EGRESO', 'TRANSFERENCIA'
    subtype: str
    account_id: int
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None
    amount_original: float
    currency: str
    exchange_rate: float = 1.0
    amount_usd: Optional[float] = None
    reference_number: Optional[str] = ""
    beneficiary: Optional[str] = ""
    description: Optional[str] = ""
    doc_type: Optional[str] = "FACTURA_FISCAL"
    doc_number: Optional[str] = ""
    is_credit: Optional[bool] = False
    credit_status: Optional[str] = "PAGADO"
    tax_retention_amount: Optional[float] = 0.0
    tax_retention_proof: Optional[str] = ""
    pos_terminal: Optional[str] = ""
    pos_lot_number: Optional[str] = ""

class TransferCreate(BaseModel):
    date: datetime.date
    origin_account_id: int
    destination_account_id: int
    amount_origin: float
    amount_destination: float
    exchange_rate: float = 1.0
    reference_number: Optional[str] = ""
    description: Optional[str] = "Traspaso / Cambio de divisas"
