import os
import json
import uuid
import datetime
import urllib.request
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from fastapi import HTTPException

from models import (
    Branch, CashRegister, User, BudgetCategory, TreasuryAccount,
    AccountMonthlyBalance, Supplier, SystemSetting, Transaction,
    DailyCashClose, AuditLog
)
from core.config import MASTER_ADMIN_KEY
from core.audit import record_audit

# Lista ordenada topológicamente (Padres primero, dependientes después)
TABLE_MODELS = [
    ("branches", Branch),
    ("cash_registers", CashRegister),
    ("users", User),
    ("budget_categories", BudgetCategory),
    ("treasury_accounts", TreasuryAccount),
    ("account_monthly_balances", AccountMonthlyBalance),
    ("suppliers", Supplier),
    ("system_settings", SystemSetting),
    ("transactions", Transaction),
    ("daily_cash_closes", DailyCashClose),
    ("audit_logs", AuditLog),
]

def mask_credential(val: Optional[str]) -> str:
    if not val:
        return "NOT_CONFIGURED"
    if len(val) <= 6:
        return "******"
    return val[:4] + "*" * (len(val) - 6) + val[-2:]

def get_s3_config() -> Optional[Dict[str, str]]:
    endpoint = os.environ.get("S3_ENDPOINT_URL")
    bucket = os.environ.get("S3_BUCKET")
    access_key = os.environ.get("S3_ACCESS_KEY_ID")
    secret_key = os.environ.get("S3_SECRET_ACCESS_KEY")
    region = os.environ.get("S3_REGION", "auto")

    if endpoint and bucket and access_key and secret_key:
        return {
            "endpoint": endpoint,
            "bucket": bucket,
            "access_key": access_key,
            "secret_key": secret_key,
            "region": region
        }
    return None

def upload_to_s3_compatible(file_path: str, backup_filename: str) -> bool:
    config = get_s3_config()
    if not config:
        return False

    try:
        # Si boto3 está disponible, usarlo
        import boto3
        from botocore.config import Config
        s3_client = boto3.client(
            's3',
            endpoint_url=config["endpoint"],
            aws_access_key_id=config["access_key"],
            aws_secret_access_key=config["secret_key"],
            region_name=config["region"],
            config=Config(signature_version='s3v4')
        )
        s3_client.upload_file(file_path, config["bucket"], backup_filename)
        return True
    except ImportError:
        print("[WARN] boto3 no está instalado; subida remota omitida.")
        return False
    except Exception as e:
        print(f"[ERROR] Error al subir backup a almacenamiento remoto: {e}")
        return False

def generate_deterministic_backup(db: Session, user: Optional[User] = None, ip_address: str = "") -> Dict[str, Any]:
    backup_id = str(uuid.uuid4())[:8]
    now = datetime.datetime.now(datetime.timezone.utc)
    ts_str = now.strftime("%Y%m%d_%H%M%S")
    backup_filename = f"TEV_BACKUP_{ts_str}_{backup_id}.json"

    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    local_file_path = os.path.join(backup_dir, backup_filename)

    engine_name = db.bind.dialect.name
    tables_data = {}
    total_records = 0

    for table_name, model_cls in TABLE_MODELS:
        records = db.query(model_cls).all()
        table_rows = []
        for r in records:
            row_dict = {}
            for col in r.__table__.columns:
                val = getattr(r, col.name)
                if isinstance(val, (datetime.datetime, datetime.date)):
                    row_dict[col.name] = val.isoformat()
                else:
                    row_dict[col.name] = val
            table_rows.append(row_dict)
        tables_data[table_name] = table_rows
        total_records += len(table_rows)

    backup_payload = {
        "metadata": {
            "version": "2.1.0",
            "backup_id": backup_id,
            "filename": backup_filename,
            "created_at": now.isoformat(),
            "engine": engine_name,
            "tables_count": len(TABLE_MODELS),
            "total_records": total_records
        },
        "tables_data": tables_data
    }

    # Escritura a disco local
    with open(local_file_path, "w", encoding="utf-8") as f:
        json.dump(backup_payload, f, indent=2, ensure_ascii=False)

    # Verificación de Integridad Post-Generación y Cálculo SHA-256
    if not os.path.exists(local_file_path) or os.path.getsize(local_file_path) == 0:
        raise HTTPException(status_code=500, detail="Fallo de integridad: Archivo de backup local vacío o no generado.")

    import hashlib
    with open(local_file_path, "rb") as f:
        file_bytes = f.read()
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    with open(local_file_path, "r", encoding="utf-8") as f:
        verified_json = json.load(f)
        if "tables_data" not in verified_json or "metadata" not in verified_json:
            raise HTTPException(status_code=500, detail="Fallo de integridad: Estructura JSON de backup corrupta.")

    # Intentar subida remota opcional
    remote_status = "NOT_CONFIGURED"
    s3_conf = get_s3_config()
    if s3_conf:
        uploaded = upload_to_s3_compatible(local_file_path, backup_filename)
        if uploaded:
            remote_status = "REMOTE_BACKUP_SUCCESS"
        else:
            remote_status = "REMOTE_BACKUP_FAILED"

    audit_details = {
        "backup_id": backup_id,
        "filename": backup_filename,
        "records": total_records,
        "sha256": sha256_hash,
        "remote_status": remote_status,
        "s3_bucket": s3_conf["bucket"] if s3_conf else None
    }
    record_audit(db, user, 'LOCAL_BACKUP_SUCCESS', 'SystemBackup', backup_id, audit_details, ip_address)
    db.commit()

    return {
        "status": "SUCCESS",
        "backup_id": backup_id,
        "filename": backup_filename,
        "total_records": total_records,
        "sha256_checksum": sha256_hash,
        "local_path": local_file_path,
        "remote_status": remote_status,
        "created_at": now.isoformat()
    }

def restore_deterministic_backup(db: Session, user: User, backup_payload: Dict[str, Any], ip_address: str = "") -> Dict[str, Any]:
    if "metadata" not in backup_payload or "tables_data" not in backup_payload:
        raise HTTPException(status_code=400, detail="Formato de backup inválido o corrupto.")

    meta = backup_payload["metadata"]
    tables_data = backup_payload["tables_data"]

    # 1. Purgado en orden inverso topológico (Hijas primero, Padres al final)
    for table_name, model_cls in reversed(TABLE_MODELS):
        db.query(model_cls).delete()
    db.flush()

    # 2. Inserción en orden topológico (Padres primero, Hijas al final)
    restored_counts = {}
    for table_name, model_cls in TABLE_MODELS:
        rows = tables_data.get(table_name, [])
        for r_dict in rows:
            clean_dict = {}
            for col in model_cls.__table__.columns:
                if col.name in r_dict:
                    val = r_dict[col.name]
                    # Parsear fechas si corresponde
                    if col.type.python_type in (datetime.datetime, datetime.date) and isinstance(val, str):
                        try:
                            if col.type.python_type == datetime.date:
                                clean_dict[col.name] = datetime.datetime.fromisoformat(val).date()
                            else:
                                clean_dict[col.name] = datetime.datetime.fromisoformat(val)
                        except Exception:
                            clean_dict[col.name] = val
                    else:
                        clean_dict[col.name] = val
            instance = model_cls(**clean_dict)
            db.add(instance)
        db.flush()
        restored_counts[table_name] = len(rows)

    # 3. Sincronización de secuencias en PostgreSQL si aplica
    if db.bind.dialect.name == 'postgresql':
        for table_name, _ in TABLE_MODELS:
            try:
                db.execute(text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM {table_name};"))
            except Exception as e:
                print(f"[WARN] No se pudo reajustar secuencia de {table_name}: {e}")

    record_audit(db, user, 'RESTORE_BACKUP_SUCCESS', 'SystemBackup', meta.get("backup_id", "UNKNOWN"), {
        "original_filename": meta.get("filename"),
        "restored_counts": restored_counts
    }, ip_address)
    db.commit()

    return {
        "status": "RESTORE_SUCCESS",
        "backup_id": meta.get("backup_id"),
        "restored_tables": len(restored_counts),
        "total_records_restored": sum(restored_counts.values())
    }

def clean_slate_database(db: Session, user: User, master_key: str, confirmation: str, ip_address: str = ""):
    if master_key != MASTER_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Clave Maestra de Gobernanza Incorrecta.")
    if confirmation != "CONFIRMAR-PURGA-TEV":
        raise HTTPException(status_code=400, detail="Frase de confirmación inválida. Debe escribir exactamente 'CONFIRMAR-PURGA-TEV'.")

    # Purgar transacciones operativas respetando orden topológico
    db.query(DailyCashClose).delete()
    db.query(Transaction).delete()
    db.query(AuditLog).delete()

    # Restablecer saldos iniciales de cuentas a 0
    for acc in db.query(TreasuryAccount).all():
        acc.initial_balance = 0.0

    record_audit(db, user, 'CLEAN_SLATE_RESET', 'System', 'ALL', {'purged': True}, ip_address)
    db.commit()
    return {"message": "Puesta a Cero ejecutada con éxito. Todos los catálogos de valor permanecen intactos."}
