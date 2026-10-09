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

import hashlib
import gzip
import zlib
import subprocess
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover
    boto3 = None
    Config = None
    BotoCoreError = Exception
    ClientError = Exception


def mask_credential(val: Optional[str]) -> str:
    if not val:
        return "NOT_CONFIGURED"
    if len(val) <= 6:
        return "******"
    return val[:4] + "*" * (len(val) - 6) + val[-2:]

def calculate_file_sha256(file_path: str) -> str:
    """Calcula el checksum SHA-256 de un archivo en streaming de chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# Alias para compatibilidad de suite
calculate_sha256 = calculate_file_sha256

def verify_backup_integrity(file_path: str, expected_sha256: str) -> bool:
    """Verifica si el hash SHA-256 de un archivo coincide exactamente con el esperado."""
    if not os.path.exists(file_path):
        return False
    actual_hash = calculate_file_sha256(file_path)
    return actual_hash.lower() == expected_sha256.lower()

# Alias
verify_sha256 = verify_backup_integrity

def decompress_backup(file_path: str) -> bytes:
    """Descomprime un archivo gzip validando su cabecera y consistencia."""
    try:
        with gzip.open(file_path, "rb") as gz:
            return gz.read()
    except (zlib.error, EOFError) as e:
        raise gzip.BadGzipFile(f"Archivo GZIP corrupto o truncado: {e}") from e


def get_s3_config() -> Optional[Dict[str, str]]:
    endpoint = os.environ.get("S3_ENDPOINT_URL") or (
        f"https://{os.environ.get('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com"
        if os.environ.get("R2_ACCOUNT_ID") else None
    )
    bucket = os.environ.get("S3_BUCKET") or os.environ.get("R2_BUCKET_NAME")
    access_key = os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ.get("R2_SECRET_ACCESS_KEY")
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

def get_r2_client():
    """Retorna un cliente boto3 configurado para Cloudflare R2 / S3 o None."""
    config = get_s3_config()
    if not config:
        return None
    try:
        import boto3
        from botocore.config import Config
        return boto3.client(
            's3',
            endpoint_url=config["endpoint"],
            aws_access_key_id=config["access_key"],
            aws_secret_access_key=config["secret_key"],
            region_name=config["region"],
            config=Config(signature_version='s3v4')
        )
    except Exception as e:
        return e

def upload_to_s3_compatible(file_path: str, backup_filename: Optional[str] = None) -> bool:
    if backup_filename is None:
        backup_filename = os.path.basename(file_path)

    config = get_s3_config()
    if not config:
        return False

    try:
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
    except ImportError:  # pragma: no cover
        print("[WARN] boto3 no está instalado; subida remota omitida.")
        return False
    except Exception as e:
        print(f"[ERROR] Error al subir backup a almacenamiento remoto: {e}")
        raise RuntimeError(f"Fallo de conexión o subida a R2/S3: {e}") from e

# Alias para la suite
upload_to_r2 = upload_to_s3_compatible
upload_backup = upload_to_s3_compatible

def download_from_s3_compatible(backup_filename: str, target_local_path: str) -> bool:
    config = get_s3_config()
    if not config:
        return False

    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        s3_client = boto3.client(
            's3',
            endpoint_url=config["endpoint"],
            aws_access_key_id=config["access_key"],
            aws_secret_access_key=config["secret_key"],
            region_name=config["region"],
            config=Config(signature_version='s3v4')
        )
        s3_client.download_file(config["bucket"], backup_filename, target_local_path)
        return True
    except ImportError:  # pragma: no cover
        print("[WARN] boto3 no está instalado; descarga remota omitida.")
        return False

    except Exception as e:
        print(f"[ERROR] Error al descargar backup desde almacenamiento remoto: {e}")
        # Si es NoSuchKey o 404, levantar FileNotFoundError o propagar
        if "NoSuchKey" in str(e) or (hasattr(e, "response") and e.response.get("Error", {}).get("Code") == "NoSuchKey"):
            raise FileNotFoundError(f"Snapshot no encontrado en almacenamiento remoto: {backup_filename}") from e
        raise RuntimeError(f"Fallo en descarga R2/S3: {e}") from e

# Alias para la suite
download_from_r2 = download_from_s3_compatible
download_backup = download_from_s3_compatible

def delete_from_s3_compatible(backup_filename: str) -> bool:
    config = get_s3_config()
    if not config:
        return False

    try:
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
        s3_client.delete_object(Bucket=config["bucket"], Key=backup_filename)
        return True
    except Exception as e:
        print(f"[WARN] Error al eliminar backup remoto {backup_filename}: {e}")
        return False

def dump_database(output_path: Optional[str] = None) -> str:
    """Ejecuta pg_dump en modo subprocess si la base de datos es PostgreSQL."""
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        cmd = ["pg_dump", db_url]
        res = subprocess.run(cmd, check=True, capture_output=True)
        return res.stdout.decode("utf-8")
    return ""

def prune_backups_fifo(
    max_backups: Optional[int] = None,
    max_days: Optional[int] = None,
    db: Optional[Session] = None,
    backup_dir: Optional[str] = None
) -> Dict[str, Any]:
    from core.config import FIFO_BACKUP_MAX_COUNT, FIFO_BACKUP_RETENTION_DAYS
    limit_count = max_backups if max_backups is not None else FIFO_BACKUP_MAX_COUNT
    limit_days = max_days if max_days is not None else FIFO_BACKUP_RETENTION_DAYS

    target_dir = backup_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
    if not os.path.exists(target_dir):
        return {"pruned_count": 0, "remaining_count": 0, "pruned_files": []}


    files = []
    for f in os.listdir(target_dir):
        if (f.startswith("TEV_BACKUP_") or f.startswith("backup_")) and (f.endswith(".json") or f.endswith(".sql.gz") or f.endswith(".gz")):
            full_path = os.path.join(target_dir, f)
            try:
                mtime = os.path.getmtime(full_path)
                files.append({
                    "filename": f,
                    "path": full_path,
                    "mtime": mtime,
                    "datetime": datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
                })
            except Exception:
                pass

    # Ordenar cronológicamente (el más viejo primero para cola FIFO)
    files.sort(key=lambda x: x["mtime"])

    pruned = []
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Purgar por antigüedad (días de retención)
    surviving_files = []
    for item in files:
        age_days = (now - item["datetime"]).total_seconds() / 86400.0
        if age_days > limit_days:
            try:
                Path(item["path"]).unlink()
                delete_from_s3_compatible(item["filename"])
                pruned.append(item["filename"])
            except Exception as e:
                print(f"[WARN] Error purgando {item['filename']}: {e}")
        else:
            surviving_files.append(item)

    # 2. Purgar por cuota máxima (FIFO: descartar los más viejos de la cabeza)
    while len(surviving_files) > limit_count:
        oldest = surviving_files.pop(0)
        try:
            Path(oldest["path"]).unlink()
            delete_from_s3_compatible(oldest["filename"])
            pruned.append(oldest["filename"])
        except Exception as e:
            print(f"[WARN] Error purgando por cupo FIFO {oldest['filename']}: {e}")


    if db and pruned:
        try:
            record_audit(db, None, 'FIFO_BACKUPS_PRUNED', 'SystemBackup', 'FIFO_QUEUE', {
                'pruned_count': len(pruned),
                'pruned_files': pruned,
                'remaining_count': len(surviving_files)
            })
            db.commit()
        except Exception as e:
            print(f"[WARN] Error registrando auditoría FIFO: {e}")

    return {
        "pruned_count": len(pruned),
        "remaining_count": len(surviving_files),
        "pruned_files": pruned,
        "max_capacity": limit_count
    }


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

    # Ejecución automática de poda FIFO en cada generación
    fifo_result = prune_backups_fifo(db=db)

    return {
        "status": "SUCCESS",
        "backup_id": backup_id,
        "filename": backup_filename,
        "total_records": total_records,
        "sha256_checksum": sha256_hash,
        "local_path": local_file_path,
        "remote_status": remote_status,
        "created_at": now.isoformat(),
        "fifo_prune": fifo_result
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

def create_backup(db: Optional[Session] = None, user: Optional[User] = None, ip_address: str = ""):
    """Wrapper universal para creación de backup compatible con llamadas directas y pg_dump."""
    dump_database()
    if db is None:
        from database import SessionLocal
        local_db = SessionLocal()
        try:
            return generate_deterministic_backup(local_db, user, ip_address)
        finally:
            local_db.close()
    return generate_deterministic_backup(db, user, ip_address)

def restore_backup(file_path_or_payload, db: Optional[Session] = None, user: Optional[User] = None, expected_sha256: Optional[str] = None):
    """Restaura un backup verificando hash criptográfico SHA-256 e integridad previa."""
    if isinstance(file_path_or_payload, str):
        if not os.path.exists(file_path_or_payload):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path_or_payload}")
        if expected_sha256:
            calc_hash = calculate_file_sha256(file_path_or_payload)
            if calc_hash.lower() != expected_sha256.lower():
                raise ValueError(f"Fallo de integridad SHA-256: Hash esperado {expected_sha256} no coincide con {calc_hash}")
        with open(file_path_or_payload, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = file_path_or_payload

    if db is None:
        from database import SessionLocal
        local_db = SessionLocal()
        try:
            return restore_deterministic_backup(local_db, user or User(), payload)
        finally:
            local_db.close()
    return restore_deterministic_backup(db, user or User(), payload)

