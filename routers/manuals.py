import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from database import get_db
from models import User
from core.security import get_current_user, get_optional_current_user

router = APIRouter(prefix="/api/manuals", tags=["Manuales de Usuario"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MANUAL_FILES = {
    "cajera": {
        "filename": "MANUAL_CAJERA.md",
        "title": "👩‍💼 Manual Operativo: Cajera (Punto de Venta y Arqueo)",
        "allowed_roles": ["cajera", "administradora", "directivo"]
    },
    "administradora": {
        "filename": "MANUAL_ADMINISTRADORA.md",
        "title": "👩‍💻 Manual de Gestión: Administradora (Tesorería Central)",
        "allowed_roles": ["administradora", "directivo"]
    },
    "directivo": {
        "filename": "MANUAL_DIRECTIVO.md",
        "title": "👔 Manual Estratégico: Directivo (Gerencia y Finanzas)",
        "allowed_roles": ["directivo"]
    }
}

@router.get("/{role}")
def get_manual_content(
    role: str,
    current_user: User = Depends(get_current_user)
):
    role_key = role.lower()
    if role_key not in MANUAL_FILES:
        raise HTTPException(status_code=404, detail="Manual no encontrado.")
    
    config = MANUAL_FILES[role_key]
    if current_user.role not in config["allowed_roles"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tiene permisos para ver el manual de {role}."
        )
    
    file_path = os.path.join(BASE_DIR, config["filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo del manual no disponible en el servidor.")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {
        "role": role_key,
        "title": config["title"],
        "content": content
    }

@router.get("/{role}/download")
def download_manual_file(
    role: str,
    current_user: User = Depends(get_optional_current_user)
):
    role_key = role.lower()
    if role_key not in MANUAL_FILES:
        raise HTTPException(status_code=404, detail="Manual no encontrado.")
    
    config = MANUAL_FILES[role_key]
    file_path = os.path.join(BASE_DIR, config["filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo del manual no disponible.")
    
    return FileResponse(
        path=file_path,
        filename=config["filename"],
        media_type="text/markdown"
    )
