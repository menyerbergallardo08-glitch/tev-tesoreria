import asyncio
import datetime
from database import SessionLocal
from services.backup_service import generate_deterministic_backup, prune_backups_fifo

_scheduler_task = None
_running = False

async def backup_scheduler_worker():
    global _running
    _running = True
    print("[SCHEDULER] Servicio de Backups Automaticos Diarios (FIFO) Iniciado.")

    while _running:
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            target = now.replace(hour=23, minute=59, second=0, microsecond=0)
            if now >= target:
                target += datetime.timedelta(days=1)
            seconds_until = (target - now).total_seconds()
            print(f"[SCHEDULER] Proximo backup programado en {seconds_until/3600:.2f} h (23:59:00 UTC).")
            await asyncio.sleep(min(seconds_until, 3600))
            now_check = datetime.datetime.now(datetime.timezone.utc)
            if now_check.hour == 23 and now_check.minute >= 58:
                print("[SCHEDULER] Ejecutando Snapshot Deterministico Diario y Rotacion FIFO...")
                db = SessionLocal()
                try:
                    res = generate_deterministic_backup(db, user=None, ip_address="SCHEDULER_LOCAL")
                    print(f"[SCHEDULER] Backup automatico completado: {res.get('filename')}")
                except Exception as e:
                    print(f"[SCHEDULER] [ERROR] Fallo en backup automatico: {e}")
                finally:
                    db.close()
                await asyncio.sleep(120)
        except asyncio.CancelledError:
            print("[SCHEDULER] Worker de backup cancelado ordenadamente.")
            break
        except Exception as e:
            print(f"[SCHEDULER] [WARN] Excepcion no critica en worker: {e}")
            await asyncio.sleep(300)

def start_scheduler():
    global _scheduler_task
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            _scheduler_task = asyncio.create_task(backup_scheduler_worker())
    except Exception as e:
        print(f"[SCHEDULER] No se pudo vincular al event loop: {e}")

def stop_scheduler():
    global _running, _scheduler_task
    _running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
