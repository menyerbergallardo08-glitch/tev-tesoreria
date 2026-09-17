from pydantic import BaseModel, Field
from typing import Optional

class ExpenseCreate(BaseModel):
    date: str
    category_id: int
    account_id: int
    amount_usd: float = Field(..., gt=0)
    currency: str = 'USD'
    exchange_rate: Optional[float] = 1.0
    amount_original: Optional[float] = 0.0
    subtype: str = 'GASTO_OPERATIVO' # 'GASTO_OPERATIVO', 'PAGO_PROVEEDOR', 'RETIRO_ACCIONISTA', 'VALE_CAJA'
    beneficiary: str
    reference_number: Optional[str] = None
    doc_number: Optional[str] = None
    description: Optional[str] = ''
    tax_retention_amount: Optional[float] = 0.0
    tax_retention_proof: Optional[str] = None

class RetentionAddRequest(BaseModel):
    tax_retention_amount: float = Field(..., gt=0)
    tax_retention_proof: str

class SupplierCreate(BaseModel):
    name: str
    rif: Optional[str] = ''
    phone: Optional[str] = ''
    bank_details: Optional[str] = ''
