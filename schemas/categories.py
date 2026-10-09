from pydantic import BaseModel
from typing import Optional

class CategoryCreate(BaseModel):
    code: int
    name: str
    monthly_budget_usd: float = 0.0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    monthly_budget_usd: Optional[float] = None
    is_active: Optional[bool] = None
