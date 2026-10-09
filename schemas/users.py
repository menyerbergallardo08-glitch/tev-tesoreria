from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str # 'cajera', 'administradora', 'directivo'
    branch_id: Optional[int] = None

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserPasswordReset(BaseModel):
    new_password: str
