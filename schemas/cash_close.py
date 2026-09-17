from pydantic import BaseModel
from typing import Optional, Dict

class CashCloseCreate(BaseModel):
    date: str
    profit_sales_total_usd: float = 0.0
    sales_fiscal_iva_usd: float = 0.0
    sales_notes_credit_usd: float = 0.0
    sales_notes_collected_usd: float = 0.0
    returns_total_usd: float = 0.0
    cash_usd_physical: float = 0.0
    cash_ves_physical: float = 0.0
    pos_total_usd: float = 0.0
    bank_transfers_usd: float = 0.0
    cashea_usd: float = 0.0
    retentions_iva_usd: float = 0.0
    retentions_islr_usd: float = 0.0
    expenses_caja_usd: float = 0.0
    total_expected_usd: float = 0.0
    difference_usd: float = 0.0
    status: str = 'CUADRADO' # 'CUADRADO', 'SOBRANTE', 'FALTANTE'
    arqueo_usd_json: Optional[str] = '{}'
    arqueo_ves_json: Optional[str] = '{}'
    pos_details_json: Optional[str] = '{}'
    notes: Optional[str] = ''
