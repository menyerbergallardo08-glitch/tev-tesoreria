import ssl
import re
import json
import urllib.request
import datetime
from typing import Optional
from sqlalchemy.orm import Session
from models import SystemSetting

def fetch_bcv_official_rate() -> Optional[float]:
    # 1. FUENTE PRIMARIA: Web Oficial del BCV
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            "https://www.bcv.org.ve/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=8, context=ctx) as response:
            if response.status == 200:
                html = response.read().decode("utf-8", errors="ignore")
                idx = html.find('id="dolar"')
                if idx != -1:
                    chunk = html[idx:idx+800]
                    m = re.search(r'<strong[^>]*>\s*([0-9.,]+)\s*<\/strong>', chunk)
                    if m:
                        raw_str = m.group(1).strip()
                        norm_str = raw_str.replace('.', '').replace(',', '.') if ',' in raw_str else raw_str
                        rate_val = float(norm_str)
                        if rate_val > 10.0:
                            return round(rate_val, 4)
    except Exception as e:
        print(f"[WARN] Error consultando bcv.org.ve: {e}")

    # 2. FUENTE SECUNDARIA: DolarAPI
    try:
        req = urllib.request.Request("https://ve.dolarapi.com/v1/dolares/oficial", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if "promedio" in data and isinstance(data["promedio"], (int, float)):
                    return round(float(data["promedio"]), 4)
    except Exception as e:
        print(f"[WARN] Error DolarAPI fallback: {e}")

    return None

def _upsert_setting(db: Session, key: str, value: str) -> None:
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        db.add(SystemSetting(key=key, value=value))
    else:
        setting.value = value


def resolve_effective_bcv_rate(
    db: Session,
    now_dt: Optional[datetime.datetime] = None,
    mock_fresh_rate: Optional[float] = None,
    force_sync: bool = False
) -> dict:
    tz_ve = datetime.timezone(datetime.timedelta(hours=-4))
    if now_dt is not None:
        now_ve = now_dt if now_dt.tzinfo else now_dt.replace(tzinfo=tz_ve)
    else:
        now_ve = datetime.datetime.now(tz_ve)
    weekday = now_ve.weekday()
    current_minutes = now_ve.hour * 60 + now_ve.minute
    cutoff_430 = 16 * 60 + 30

    fresh_rate = mock_fresh_rate if mock_fresh_rate is not None else fetch_bcv_official_rate()
    setting_active = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv').first()
    setting_friday = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv_viernes').first()
    setting_next_monday = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv_proximo_lunes').first()

    current_val = float(setting_active.value) if (setting_active and setting_active.value) else 848.55
    if current_val < 100.0:
        current_val = fresh_rate if (fresh_rate and fresh_rate > 100.0) else 848.55
        if setting_active:
            setting_active.value = str(current_val)
        else:
            db.add(SystemSetting(key='tasa_bcv', value=str(current_val)))
        db.commit()

    today_str = now_ve.strftime('%Y-%m-%d')

    if not force_sync and weekday == 4 and current_minutes >= cutoff_430:
        if fresh_rate and fresh_rate > 100.0:
            _upsert_setting(db, 'tasa_bcv_viernes', str(current_val))
            _upsert_setting(db, 'tasa_bcv_viernes_fecha', today_str)
            _upsert_setting(db, 'tasa_bcv_proximo_lunes', str(fresh_rate))
            db.commit()
            
        return {
            "rate": current_val,
            "policy_applied": "Viernes tarde / Fin de semana (Se mantiene tasa de cierre del Viernes hasta el Domingo 12:00 de la noche)",
            "next_rate_monday": float(setting_next_monday.value) if setting_next_monday else (fresh_rate or current_val),
            "synced": True
        }

    if not force_sync and weekday in (5, 6):
        friday_str = (now_ve - datetime.timedelta(days=(weekday - 4))).strftime('%Y-%m-%d')
        setting_friday_date = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv_viernes_fecha').first()
        is_current_friday = bool(setting_friday_date and setting_friday_date.value == friday_str)

        if is_current_friday and setting_friday and float(setting_friday.value) > 100.0:
            friday_val = float(setting_friday.value)
        else:
            friday_val = current_val if current_val > 100.0 else (fresh_rate or 848.55)
            _upsert_setting(db, 'tasa_bcv_viernes', str(friday_val))
            _upsert_setting(db, 'tasa_bcv_viernes_fecha', friday_str)
            db.commit()

        return {
            "rate": friday_val,
            "policy_applied": "Fin de semana (Tasa de cierre del Viernes)",
            "next_rate_monday": float(setting_next_monday.value) if setting_next_monday else (fresh_rate or current_val),
            "synced": True
        }

    # Política de Lunes a Jueves después de las 4:00 PM (16:00)
    # El BCV publica la tasa del día siguiente, pero en tienda se sigue facturando a la tasa del día en curso.
    # Si el usuario pulsa explícitamente "Sincronizar" (force_sync=True), sí se actualiza a la tasa oficial vigente.
    cutoff_400 = 16 * 60  # 16:00
    if not force_sync and weekday in (0, 1, 2, 3) and current_minutes >= cutoff_400:
        # Si hoy aún no se había actualizado la tasa matutina (ej. el servidor estuvo caído en la mañana),
        # promover la tasa programada para hoy (tasa_bcv_proximo_lunes en lunes, o tasa_bcv_siguiente_dia).
        setting_last_sync_date = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv_fecha').first()
        if not (setting_last_sync_date and setting_last_sync_date.value == today_str):
            scheduled_key = 'tasa_bcv_proximo_lunes' if weekday == 0 else 'tasa_bcv_siguiente_dia'
            scheduled_setting = db.query(SystemSetting).filter(SystemSetting.key == scheduled_key).first()
            if scheduled_setting and scheduled_setting.value:
                try:
                    sched_val = float(scheduled_setting.value)
                    if sched_val > 100.0 and sched_val != current_val:
                        current_val = sched_val
                        _upsert_setting(db, 'tasa_bcv', str(current_val))
                        _upsert_setting(db, 'bcv_rate', str(current_val))
                        _upsert_setting(db, 'tasa_bcv_fecha', today_str)
                except ValueError:
                    pass

        setting_next_day = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv_siguiente_dia').first()
        if fresh_rate and fresh_rate > 100.0:
            _upsert_setting(db, 'tasa_bcv_siguiente_dia', str(fresh_rate))
            db.commit()

        next_val = fresh_rate if (fresh_rate and fresh_rate > 100.0) else (float(setting_next_day.value) if setting_next_day else current_val)
        return {
            "rate": current_val,
            "policy_applied": "Jornada en curso (Tasa del día congelada; la tasa del BCV de la tarde regirá a partir de mañana)",
            "next_rate_tomorrow": next_val,
            "synced": True
        }

    # Respetar ajuste manual realizado hoy salvo sincronización explícita (force_sync) o pruebas unitarias
    setting_manual_date = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv_manual_fecha').first()
    if not force_sync and mock_fresh_rate is None and setting_manual_date and setting_manual_date.value == today_str:
        return {
            "rate": current_val,
            "policy_applied": "Tasa Manual Fijada Hoy",
            "synced": False
        }

    # Durante la mañana / primera mitad del día antes de las 4:00 PM (o sincronización explícita): actualizar si hay tasa fresca
    if fresh_rate and fresh_rate > 100.0:
        if force_sync and setting_manual_date:
            setting_manual_date.value = ''
        if fresh_rate != current_val:
            _upsert_setting(db, 'tasa_bcv', str(fresh_rate))
            _upsert_setting(db, 'bcv_rate', str(fresh_rate))
            _upsert_setting(db, 'tasa_bcv_fecha', today_str)
            db.commit()
            current_val = fresh_rate
        else:
            _upsert_setting(db, 'tasa_bcv_fecha', today_str)
            db.commit()
    else:
        # Asegurar que bcv_rate exista si tasa_bcv existe
        setting_bcv_rate = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
        if not setting_bcv_rate and current_val > 100.0:
            db.add(SystemSetting(key='bcv_rate', value=str(current_val)))
            db.commit()

    return {
        "rate": current_val,
        "policy_applied": "Tasa Oficial del Día",
        "synced": bool(fresh_rate)
    }
