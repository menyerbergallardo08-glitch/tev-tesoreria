from pydantic import BaseModel, Field
from typing import Optional

class SaleCreate(BaseModel):
    date: str
    doc_type: str = 'NOTA_ENTREGA' # 'FACTURA_FISCAL', 'NOTA_ENTREGA'
    doc_number: str
    client_name: Optional[str] = ''
    client_rif: Optional[str] = ''
    amount_usd: float = Field(..., gt=0)
    payment_method: str = 'EFECTIVO_USD'
    account_id: Optional[int] = None
    exchange_rate: Optional[float] = 1.0
    amount_ves: Optional[float] = 0.0
    is_credit: bool = False
    abono_usd: Optional[float] = 0.0
    abono_account_id: Optional[int] = None
    abono_payment_method: Optional[str] = None
    pos_terminal: Optional[str] = None
    pos_lot_number: Optional[str] = None
    reference_number: Optional[str] = None
    description: Optional[str] = ''

class SaleVoidRequest(BaseModel):
    transaction_id: int
    reason: str
