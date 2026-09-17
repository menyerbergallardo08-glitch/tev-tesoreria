from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import AuditLog, Transaction, User
from core.security import require_roles

router = APIRouter(prefix="/api/audit", tags=["Auditoría y Reportes"])

@router.get("/logs")
def get_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_roles(["directivo", "administradora"])),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [{
        "id": l.id,
        "timestamp": l.timestamp.isoformat(),
        "username": l.username,
        "action": l.action,
        "entity_type": l.entity_type,
        "entity_id": l.entity_id,
        "details": l.details_json,
        "ip_address": l.ip_address
    } for l in logs]
