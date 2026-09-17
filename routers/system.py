import os
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database import get_db
from models import User
from core.security import require_roles, get_current_user
from core.bcv import resolve_effective_bcv_rate
from schemas.system import CleanSlateRequest
from services.backup_service import (
    clean_slate_database,
    generate_deterministic_backup,
    restore_deterministic_backup
)
from core.config import MASTER_ADMIN_KEY

router = APIRouter(prefix="/api/system", tags=["Sistema y Gobernanza"])

class RestoreRequest(BaseModel):
    master_key: str
    backup_data: Dict[str, Any]

@router.get("/bcv-rate")
def get_bcv_rate(db: Session = Depends(get_db)):
    return resolve_effective_bcv_rate(db)

@router.post("/backup")
def create_backup(
    request: Request,
    current_user: User = Depends(require_roles(["directivo", "administradora"])),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    return generate_deterministic_backup(db, current_user, ip)

@router.post("/restore")
def restore_backup(
    data: RestoreRequest,
    request: Request,
    current_user: User = Depends(require_roles(["directivo"])),
    db: Session = Depends(get_db)
):
    if data.master_key != MASTER_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Clave Maestra de Gobernanza Incorrecta.")
    ip = request.client.host if request.client else ""
    return restore_deterministic_backup(db, current_user, data.backup_data, ip)

@router.get("/backups")
def list_local_backups(
    current_user: User = Depends(require_roles(["directivo", "administradora"]))
):
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
    if not os.path.exists(backup_dir):
        return []
    
    files = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        if f.endswith(".json"):
            fp = os.path.join(backup_dir, f)
            files.append({
                "filename": f,
                "size_bytes": os.path.getsize(fp),
                "modified_at": os.path.getmtime(fp)
            })
    return files

@router.post("/clean-slate")
def reset_system(
    data: CleanSlateRequest,
    request: Request,
    current_user: User = Depends(require_roles(["directivo"])),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    return clean_slate_database(db, current_user, data.master_key, data.confirmation_phrase, ip)
