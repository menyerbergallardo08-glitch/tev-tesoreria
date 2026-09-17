import re
from typing import Optional
from fastapi import HTTPException

def validate_and_format_retention_proof(proof_raw: Optional[str], amount: Optional[float] = 0.0) -> str:
    """
    NORMATIVA SENIAT (Providencia SNAT/2015/0049):
    El Número de Comprobante de Retención de IVA / ISLR debe constar de exactamente 14 dígitos numéricos:
    - Primeros 4 dígitos: Año fiscal (AAAA)
    - Siguientes 2 dígitos: Mes fiscal (MM, 01 a 12)
    - Últimos 8 dígitos: Correlativo numérico secuencial (CCCCCCCC)
    """
    if not proof_raw:
        if amount and amount > 0:
            raise HTTPException(
                status_code=400,
                detail="Normativa SENIAT: Debe indicar el Número de Comprobante de Retención (14 dígitos) si registró un monto retenido."
            )
        return ""

    raw = str(proof_raw).strip()
    if not raw:
        if amount and amount > 0:
            raise HTTPException(
                status_code=400,
                detail="Normativa SENIAT: Debe indicar el Número de Comprobante de Retención (14 dígitos) si registró un monto retenido."
            )
        return ""

    if raw and (amount is None or amount <= 0):
        raise HTTPException(
            status_code=400,
            detail="Normativa Fiscal: Si ingresa un Número de Comprobante de Retención, el monto retenido debe ser mayor a $0.00."
        )

    digits_only = re.sub(r'[^0-9]', '', raw)
    
    # 14 dígitos continuos
    if len(digits_only) == 14:
        year = int(digits_only[:4])
        month = int(digits_only[4:6])
        if year < 2000 or year > 2099:
            raise HTTPException(
                status_code=400,
                detail=f"Normativa SENIAT: El año '{year}' en el comprobante no es válido (2000-2099)."
            )
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=400,
                detail=f"Normativa SENIAT: El mes '{digits_only[4:6]}' no es válido (01-12)."
            )
        return digits_only

    # Con separadores (ej: 2026-09-45)
    parts = re.split(r'[-/.\s]+', raw)
    if len(parts) == 3:
        try:
            year_part = int(parts[0])
            month_part = int(parts[1])
            seq_part = int(parts[2])
            if (2000 <= year_part <= 2099) and (1 <= month_part <= 12) and (0 <= seq_part <= 99999999):
                return f"{year_part:04d}{month_part:02d}{seq_part:08d}"
        except ValueError:
            pass

    if 7 <= len(digits_only) < 14:
        try:
            year = int(digits_only[:4])
            month = int(digits_only[4:6])
            seq = int(digits_only[6:])
            if (2000 <= year <= 2099) and (1 <= month <= 12) and (0 <= seq <= 99999999):
                return f"{year:04d}{month:02d}{seq:08d}"
        except ValueError:
            pass

    raise HTTPException(
        status_code=400,
        detail=f"Normativa SENIAT Inválida: El número de comprobante '{raw}' no cumple con la estructura obligatoria de 14 dígitos (AAAAMMCCCCCCCC)."
    )
