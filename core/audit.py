import json
from typing import Optional
from sqlalchemy.orm import Session
from models import AuditLog, User

def record_audit(
    db: Session,
    user: Optional[User],
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    details: dict,
    ip_address: str = ""
):
    try:
        username = user.username if user else "sistema"
        user_id = user.id if user else None
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else "",
            details_json=json.dumps(details, ensure_ascii=False),
            ip_address=ip_address
        )
        db.add(log_entry)
        db.flush()
    except Exception as e:
        print(f"[WARN] Failed to write audit log: {e}")
