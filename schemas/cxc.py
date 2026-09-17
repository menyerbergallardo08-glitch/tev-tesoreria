from pydantic import BaseModel, Field
from typing import Optional

class HistoricalDebtCreate(BaseModel):
    client_name: str
    client_rif: Optional[str] = ''
    doc_type: str = 'NOTA_ENTREGA'
    doc_number: str
    emission_date: str
    amount_usd: float = Field(..., gt=0)
    notes: Optional[str] = ''

class CxCPaymentCreate(BaseModel):
    transaction_id: int
    amount_usd: float = Field(..., gt=0)
    account_id: int
    payment_method: str
    exchange_rate: Optional[float] = 1.0
    reference_number: Optional[str] = None
    description: Optional[str] = ''
