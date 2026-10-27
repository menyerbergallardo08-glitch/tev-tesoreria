from pydantic import BaseModel, Field
from typing import Optional

class HistoricalDebtCreate(BaseModel):
    client_name: str
    client_rif: Optional[str] = ''
    doc_type: str = 'NOTA_ENTREGA'
    doc_number: str
    emission_date: str
    amount_usd: float = Field(..., gt=0)
    seller_code: Optional[str] = None
    seller_name: Optional[str] = None
    notes: Optional[str] = ''

class CxCPaymentCreate(BaseModel):
    transaction_id: int
    amount_usd: float = Field(..., gt=0)
    account_id: Optional[int] = None
    payment_method: str = 'ABONO_CXC'
    payment_type: Optional[str] = 'COBRO'  # 'COBRO', 'RETENCION', 'NOTA_CREDITO'
    seller_code: Optional[str] = None
    seller_name: Optional[str] = None
    exchange_rate: Optional[float] = 1.0
    reference_number: Optional[str] = None
    description: Optional[str] = ''
    retention_proof: Optional[str] = None
    retention_type: Optional[str] = None
    credit_note_ref: Optional[str] = None
    credit_note_date: Optional[str] = None
