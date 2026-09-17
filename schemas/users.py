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
