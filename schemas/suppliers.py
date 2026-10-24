from pydantic import BaseModel
from typing import Optional

class SupplierCreate(BaseModel):
    name: str
    rif: Optional[str] = ''
    phone: Optional[str] = ''
    bank_details: Optional[str] = ''

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    rif: Optional[str] = None
    phone: Optional[str] = None
    bank_details: Optional[str] = None
    is_active: Optional[bool] = None
