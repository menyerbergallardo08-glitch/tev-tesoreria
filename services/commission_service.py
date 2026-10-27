import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from models import Transaction

SELLERS_COMMISSION_CONFIG = {
    "01": {"name": "Oficina", "rate": 0.0, "is_office": True, "is_coordinator": False},
    "20": {"name": "Oficina", "rate": 0.0, "is_office": True, "is_coordinator": False},
    "23": {"name": "Orianna Montilla", "rate": 0.01, "is_office": False, "is_coordinator": True},
    "25": {"name": "Daniel Zabala", "rate": 0.05, "is_office": False, "is_coordinator": False},
    "33": {"name": "Henry", "rate": 0.01, "is_office": False, "is_coordinator": False},
    "39": {"name": "Yurima", "rate": 0.01, "is_office": False, "is_coordinator": False},
    "44": {"name": "Jenny", "rate": 0.01, "is_office": False, "is_coordinator": False},
}

COORDINATION_TEAM_CODES = ["25", "33", "39", "44"]
COORDINATION_RATE = 0.01

def calculate_commissions(db: Session, start_date: datetime.date, end_date: datetime.date) -> Dict[str, Any]:
    txs = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.status != 'ANULADO'
    ).all()

    sellers_data = {}
    for code, conf in SELLERS_COMMISSION_CONFIG.items():
        sellers_data[code] = {
            "code": code,
            "name": conf["name"],
            "rate": conf["rate"],
            "rate_pct": f"{int(conf['rate'] * 100)}%",
            "is_office": conf["is_office"],
            "is_coordinator": conf["is_coordinator"],
            "ventas_contado_usd": 0.0,
            "cxc_cobradas_usd": 0.0,
            "devoluciones_usd": 0.0,
            "base_neta_cobrada_usd": 0.0,
            "comision_directa_usd": 0.0,
            "comision_coordinacion_usd": 0.0,
            "comision_total_usd": 0.0,
            "transaction_count": 0
        }

    unassigned = {
        "code": "N/A",
        "name": "Sin Vendedor Asignado",
        "rate": 0.0,
        "rate_pct": "0%",
        "is_office": True,
        "is_coordinator": False,
        "ventas_contado_usd": 0.0,
        "cxc_cobradas_usd": 0.0,
        "devoluciones_usd": 0.0,
        "base_neta_cobrada_usd": 0.0,
        "comision_directa_usd": 0.0,
        "comision_coordinacion_usd": 0.0,
        "comision_total_usd": 0.0,
        "transaction_count": 0
    }

    for t in txs:
        raw_code = (t.seller_code or "").strip()
        target = sellers_data.get(raw_code) if raw_code in sellers_data else unassigned
        target["transaction_count"] += 1

        if t.movement_type == 'INGRESO':
            if t.subtype == 'VENTA_DIARIA':
                target["ventas_contado_usd"] += (t.amount_usd or 0.0)
            elif t.subtype in ['ABONO_CXC', 'COBRO_CXC']:
                target["cxc_cobradas_usd"] += (t.amount_usd or 0.0)

        elif t.movement_type == 'EGRESO':
            if t.subtype in ['DEVOLUCION_VENTA', 'DEVOLUCION_CLIENTE'] or t.doc_type in ['DEVOLUCION', 'NOTA_CREDITO']:
                amt = t.amount_usd if (t.amount_usd and t.amount_usd > 0) else (t.credit_original_amount_usd or 0.0)
                target["devoluciones_usd"] += amt

    team_coordination_base = 0.0
    for code, s in sellers_data.items():
        s["ventas_contado_usd"] = round(s["ventas_contado_usd"], 2)
        s["cxc_cobradas_usd"] = round(s["cxc_cobradas_usd"], 2)
        s["devoluciones_usd"] = round(s["devoluciones_usd"], 2)
        
        net_base = round(s["ventas_contado_usd"] + s["cxc_cobradas_usd"] - s["devoluciones_usd"], 2)
        s["base_neta_cobrada_usd"] = max(0.0, net_base)
        s["comision_directa_usd"] = round(s["base_neta_cobrada_usd"] * s["rate"], 2)

        if code in COORDINATION_TEAM_CODES:
            team_coordination_base += s["base_neta_cobrada_usd"]

    team_coordination_base = round(team_coordination_base, 2)
    coordination_bonus = round(team_coordination_base * COORDINATION_RATE, 2)

    if "23" in sellers_data:
        sellers_data["23"]["comision_coordinacion_usd"] = coordination_bonus
        sellers_data["23"]["comision_total_usd"] = round(sellers_data["23"]["comision_directa_usd"] + coordination_bonus, 2)

    for code, s in sellers_data.items():
        if code != "23":
            s["comision_total_usd"] = s["comision_directa_usd"]

    unassigned["base_neta_cobrada_usd"] = max(0.0, round(unassigned["ventas_contado_usd"] + unassigned["cxc_cobradas_usd"] - unassigned["devoluciones_usd"], 2))

    sellers_list = list(sellers_data.values())
    if unassigned["transaction_count"] > 0:
        sellers_list.append(unassigned)

    total_contado = round(sum(s["ventas_contado_usd"] for s in sellers_list), 2)
    total_cxc = round(sum(s["cxc_cobradas_usd"] for s in sellers_list), 2)
    total_dev = round(sum(s["devoluciones_usd"] for s in sellers_list), 2)
    total_base = round(sum(s["base_neta_cobrada_usd"] for s in sellers_list), 2)
    total_comisiones = round(sum(s["comision_total_usd"] for s in sellers_list), 2)

    coordination_detail = {
        "coordinator_name": "Orianna Montilla (23)",
        "coordination_rate_pct": "1%",
        "team_members": [
            {
                "code": c,
                "name": sellers_data[c]["name"],
                "base_neta_usd": sellers_data[c]["base_neta_cobrada_usd"]
            } for c in COORDINATION_TEAM_CODES if c in sellers_data
        ],
        "team_base_usd": team_coordination_base,
        "coordination_bonus_usd": coordination_bonus
    }

    return {
        "period": {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "label": f"{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}"
        },
        "sellers": sellers_list,
        "coordination_detail": coordination_detail,
        "totals": {
            "total_ventas_contado_usd": total_contado,
            "total_cxc_cobradas_usd": total_cxc,
            "total_devoluciones_usd": total_dev,
            "total_base_neta_usd": total_base,
            "total_comisiones_a_pagar_usd": total_comisiones
        }
    }
