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

def resolve_effective_bcv_rate(db: Session) -> dict:
    tz_ve = datetime.timezone(datetime.timedelta(hours=-4))
    now_ve = datetime.datetime.now(tz_ve)
    weekday = now_ve.weekday()
    current_minutes = now_ve.hour * 60 + now_ve.minute
    cutoff_430 = 16 * 60 + 30

    fresh_rate = fetch_bcv_official_rate()
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

    if weekday == 4 and current_minutes >= cutoff_430:
        if fresh_rate and fresh_rate > 100.0:
            if not setting_friday:
                db.add(SystemSetting(key='tasa_bcv_viernes', value=str(current_val)))
            else:
                setting_friday.value = str(current_val)
            
            if not setting_next_monday:
                db.add(SystemSetting(key='tasa_bcv_proximo_lunes', value=str(fresh_rate)))
            else:
                setting_next_monday.value = str(fresh_rate)
            db.commit()
            
        return {
            "rate": current_val,
            "policy_applied": "Viernes tarde / Fin de semana (Se mantiene tasa de cierre del Viernes hasta el Domingo 12:00 de la noche)",
            "next_rate_monday": float(setting_next_monday.value) if setting_next_monday else (fresh_rate or current_val),
            "synced": True
        }

    if weekday in (5, 6):
        friday_val = float(setting_friday.value) if (setting_friday and float(setting_friday.value) > 100.0) else current_val
        return {
            "rate": friday_val,
            "policy_applied": "Fin de semana (Tasa de cierre del Viernes)",
            "next_rate_monday": float(setting_next_monday.value) if setting_next_monday else (fresh_rate or current_val),
            "synced": True
        }

    if fresh_rate and fresh_rate > 100.0:
        if fresh_rate != current_val:
            if not setting_active:
                db.add(SystemSetting(key='tasa_bcv', value=str(fresh_rate)))
            else:
                setting_active.value = str(fresh_rate)
            db.commit()
            current_val = fresh_rate

    return {
        "rate": current_val,
        "policy_applied": "Tasa Oficial del Día",
        "synced": bool(fresh_rate)
    }
