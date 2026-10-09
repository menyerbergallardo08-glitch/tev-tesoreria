from pydantic import BaseModel
from typing import Optional

class AccountCreate(BaseModel):
    name: str
    currency: str # 'USD', 'VES', 'USDT'
    account_type: str # 'EFECTIVO', 'BANCO', 'BILLETERA'
    initial_balance: float = 0.0
    only_income: bool = False

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    account_type: Optional[str] = None
    initial_balance: Optional[float] = None
    only_income: Optional[bool] = None
    is_active: Optional[bool] = None

class MonthlyBalanceCreate(BaseModel):
    account_id: int
    month: str # 'YYYY-MM'
    initial_balance: float
