from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User
from core.security import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    require_roles,
)
from schemas.users import LoginRequest, UserCreate, PasswordChangeRequest
from core.audit import record_audit

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username, User.is_active == True).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username, "role": user.role, "name": user.full_name})
    record_audit(db, user, "LOGIN_SUCCESS", "User", str(user.id), {"role": user.role}, request.client.host if request.client else "")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "branch_id": user.branch_id
        }
    }

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "branch_id": current_user.branch_id
    }

@router.post("/change-password")
def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")
    current_user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "Contraseña actualizada exitosamente."}

@router.get("/users")
def list_users(
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return [{
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "branch_id": u.branch_id
    } for u in users]

@router.post("/users")
def create_user(
    req: UserCreate,
    current_user: User = Depends(require_roles(["directivo"])),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"El nombre de usuario '{req.username}' ya está registrado.")
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
        branch_id=req.branch_id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}
