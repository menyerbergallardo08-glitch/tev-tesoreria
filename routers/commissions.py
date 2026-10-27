import datetime
import calendar
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import User
from core.security import get_current_user
from services.commission_service import calculate_commissions, SELLERS_COMMISSION_CONFIG

router = APIRouter(prefix="/api/commissions", tags=["Comisiones de Vendedores"])

@router.get("")
def get_commissions(
    month: Optional[str] = Query(default=None, description="Formato YYYY-MM"),
    start_date: Optional[str] = Query(default=None, description="Formato YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="Formato YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.date.today()
    if start_date and end_date:
        s_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    elif month:
        parts = month.split("-")
        yr = int(parts[0])
        mo = int(parts[1])
        _, last_day = calendar.monthrange(yr, mo)
        s_date = datetime.date(yr, mo, 1)
        e_date = datetime.date(yr, mo, last_day)
    else:
        _, last_day = calendar.monthrange(today.year, today.month)
        s_date = datetime.date(today.year, today.month, 1)
        e_date = datetime.date(today.year, today.month, last_day)

    return calculate_commissions(db, s_date, e_date)

@router.get("/sellers")
def get_sellers_list(current_user: User = Depends(get_current_user)):
    return [
        {
            "code": code,
            "name": conf["name"],
            "rate_pct": f"{int(conf['rate'] * 100)}%",
            "is_coordinator": conf["is_coordinator"],
            "is_office": conf["is_office"]
        }
        for code, conf in SELLERS_COMMISSION_CONFIG.items()
    ]
