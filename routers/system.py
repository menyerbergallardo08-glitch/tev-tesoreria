import os
import json
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import FileResponse
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
    restore_deterministic_backup,
    download_from_s3_compatible
)
from core.config import MASTER_ADMIN_KEY

router = APIRouter(prefix="/api/system", tags=["Sistema y Gobernanza"])

class RestoreRequest(BaseModel):
    master_key: str
    backup_data: Dict[str, Any]

@router.get("/health")
def system_health_check(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "OK"
    except Exception:
        db_status = "UNAVAILABLE"
    
    return {
        "status": "healthy" if db_status == "OK" else "degraded",
        "application": "OK",
        "database": db_status,
        "version": "2.1.0"
    }

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

@router.get("/backups/{filename}/download")
def download_backup_file(
    filename: str,
    current_user: User = Depends(require_roles(["directivo", "administradora"]))
):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")
    
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    local_path = os.path.join(backup_dir, filename)

    if not os.path.exists(local_path):
        success = download_from_s3_compatible(filename, local_path)
        if not success or not os.path.exists(local_path):
            raise HTTPException(status_code=404, detail="Archivo de backup no encontrado en almacenamiento local ni remoto.")

    return FileResponse(
        path=local_path,
        filename=filename,
        media_type="application/json"
    )

@router.get("/backups/{filename}/content")
def get_backup_content(
    filename: str,
    current_user: User = Depends(require_roles(["directivo", "administradora"]))
):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")
    
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    local_path = os.path.join(backup_dir, filename)

    if not os.path.exists(local_path):
        success = download_from_s3_compatible(filename, local_path)
        if not success or not os.path.exists(local_path):
            raise HTTPException(status_code=404, detail="Archivo de backup no encontrado en almacenamiento local ni remoto.")

    with open(local_path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.post("/clean-slate")
def reset_system(
    data: CleanSlateRequest,
    request: Request,
    current_user: User = Depends(require_roles(["directivo"])),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else ""
    return clean_slate_database(db, current_user, data.master_key, data.confirmation_phrase, ip)
