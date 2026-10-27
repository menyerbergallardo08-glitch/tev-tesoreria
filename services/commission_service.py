# -*- coding: utf-8 -*-
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
            # Cobranza y Comisiones en Bolívares (VES / Bs.)
            "ventas_contado_bs": 0.0,
            "cxc_cobradas_bs": 0.0,
            "devoluciones_bs": 0.0,
            "base_neta_bs": 0.0,
            "comision_directa_bs": 0.0,
            "comision_coordinacion_bs": 0.0,
            "comision_total_bs": 0.0,
            # Cobranza y Comisiones en Dólares (USD $)
            "ventas_contado_usd": 0.0,
            "cxc_cobradas_usd": 0.0,
            "devoluciones_usd": 0.0,
            "base_neta_usd": 0.0,
            "base_neta_cobrada_usd": 0.0, # Retrocompatibilidad
            "comision_directa_usd": 0.0,
            "comision_coordinacion_usd": 0.0,
            "comision_total_usd": 0.0,
            # Desempeño Comercial (Total Ventas Facturadas/Despachadas en $)
            "ventas_comerciales_contado_usd": 0.0,
            "ventas_comerciales_credito_usd": 0.0,
            "ventas_comerciales_devolucion_usd": 0.0,
            "ventas_totales_usd": 0.0,
            "transaction_count": 0
        }

    unassigned = {
        "code": "N/A",
        "name": "Sin Vendedor Asignado",
        "rate": 0.0,
        "rate_pct": "0%",
        "is_office": True,
        "is_coordinator": False,
        "ventas_contado_bs": 0.0,
        "cxc_cobradas_bs": 0.0,
        "devoluciones_bs": 0.0,
        "base_neta_bs": 0.0,
        "comision_directa_bs": 0.0,
        "comision_coordinacion_bs": 0.0,
        "comision_total_bs": 0.0,
        "ventas_contado_usd": 0.0,
        "cxc_cobradas_usd": 0.0,
        "devoluciones_usd": 0.0,
        "base_neta_usd": 0.0,
        "base_neta_cobrada_usd": 0.0,
        "comision_directa_usd": 0.0,
        "comision_coordinacion_usd": 0.0,
        "comision_total_usd": 0.0,
        "ventas_comerciales_contado_usd": 0.0,
        "ventas_comerciales_credito_usd": 0.0,
        "ventas_comerciales_devolucion_usd": 0.0,
        "ventas_totales_usd": 0.0,
        "transaction_count": 0
    }

    for t in txs:
        raw_code = (t.seller_code or "").strip()
        target = sellers_data.get(raw_code) if raw_code in sellers_data else unassigned
        target["transaction_count"] += 1

        is_bs = (str(t.currency).upper() in ['VES', 'BS', 'BS.'])
        amt_orig = float(t.amount_original or 0.0)
        amt_usd = float(t.amount_usd or 0.0)

        # 1. Ingresos y Cobranzas (Cash-Basis para Comisiones)
        if t.movement_type == 'INGRESO':
            if t.subtype == 'VENTA_DIARIA':
                if is_bs:
                    target["ventas_contado_bs"] += amt_orig
                else:
                    target["ventas_contado_usd"] += (amt_orig if amt_orig > 0 else amt_usd)
                
                # Desempeño Comercial: Venta Contado ($)
                target["ventas_comerciales_contado_usd"] += amt_usd

            elif t.subtype in ['ABONO_CXC', 'COBRO_CXC']:
                if is_bs:
                    target["cxc_cobradas_bs"] += amt_orig
                else:
                    target["cxc_cobradas_usd"] += (amt_orig if amt_orig > 0 else amt_usd)

        # 2. Ventas a Crédito (Desempeño Comercial - Total de Ventas en $)
        if getattr(t, 'is_credit', False) and t.movement_type == 'INGRESO' and t.subtype == 'VENTA_DIARIA':
            cred_val = float(t.credit_original_amount_usd or 0.0)
            downpayment = amt_usd
            pending_cred = max(0.0, cred_val - downpayment)
            target["ventas_comerciales_credito_usd"] += pending_cred

        # 3. Egresos / Devoluciones / Notas de Crédito
        elif t.movement_type == 'EGRESO':
            if t.subtype in ['DEVOLUCION_VENTA', 'DEVOLUCION_CLIENTE'] or t.doc_type in ['DEVOLUCION', 'NOTA_CREDITO']:
                dev_usd = amt_usd if (amt_usd and amt_usd > 0) else float(t.credit_original_amount_usd or 0.0)
                target["ventas_comerciales_devolucion_usd"] += dev_usd

                if is_bs:
                    dev_bs = amt_orig if (amt_orig and amt_orig > 0) else (dev_usd * float(t.exchange_rate or 1.0))
                    target["devoluciones_bs"] += dev_bs
                else:
                    target["devoluciones_usd"] += dev_usd

    # Calcular Bases Netas y Comisiones Individuales
    team_coordination_base_bs = 0.0
    team_coordination_base_usd = 0.0

    for code, s in sellers_data.items():
        # Redondeos Bs
        s["ventas_contado_bs"] = round(s["ventas_contado_bs"], 2)
        s["cxc_cobradas_bs"] = round(s["cxc_cobradas_bs"], 2)
        s["devoluciones_bs"] = round(s["devoluciones_bs"], 2)
        s["base_neta_bs"] = max(0.0, round(s["ventas_contado_bs"] + s["cxc_cobradas_bs"] - s["devoluciones_bs"], 2))
        s["comision_directa_bs"] = round(s["base_neta_bs"] * s["rate"], 2)

        # Redondeos USD
        s["ventas_contado_usd"] = round(s["ventas_contado_usd"], 2)
        s["cxc_cobradas_usd"] = round(s["cxc_cobradas_usd"], 2)
        s["devoluciones_usd"] = round(s["devoluciones_usd"], 2)
        s["base_neta_usd"] = max(0.0, round(s["ventas_contado_usd"] + s["cxc_cobradas_usd"] - s["devoluciones_usd"], 2))
        s["base_neta_cobrada_usd"] = s["base_neta_usd"] # Retrocompatibilidad
        s["comision_directa_usd"] = round(s["base_neta_usd"] * s["rate"], 2)

        # Desempeño Comercial ($)
        s["ventas_comerciales_contado_usd"] = round(s["ventas_comerciales_contado_usd"], 2)
        s["ventas_comerciales_credito_usd"] = round(s["ventas_comerciales_credito_usd"], 2)
        s["ventas_comerciales_devolucion_usd"] = round(s["ventas_comerciales_devolucion_usd"], 2)
        s["ventas_totales_usd"] = max(0.0, round(
            s["ventas_comerciales_contado_usd"] + s["ventas_comerciales_credito_usd"] - s["ventas_comerciales_devolucion_usd"], 2
        ))

        if code in COORDINATION_TEAM_CODES:
            team_coordination_base_bs += s["base_neta_bs"]
            team_coordination_base_usd += s["base_neta_usd"]

    team_coordination_base_bs = round(team_coordination_base_bs, 2)
    team_coordination_base_usd = round(team_coordination_base_usd, 2)
    coordination_bonus_bs = round(team_coordination_base_bs * COORDINATION_RATE, 2)
    coordination_bonus_usd = round(team_coordination_base_usd * COORDINATION_RATE, 2)

    # El Vendedor 23 (Orianna) comisiona su 1% individual y el bono de coordinación
    if "23" in sellers_data:
        sellers_data["23"]["comision_coordinacion_bs"] = coordination_bonus_bs
        sellers_data["23"]["comision_coordinacion_usd"] = coordination_bonus_usd
        sellers_data["23"]["comision_total_bs"] = round(sellers_data["23"]["comision_directa_bs"] + coordination_bonus_bs, 2)
        sellers_data["23"]["comision_total_usd"] = round(sellers_data["23"]["comision_directa_usd"] + coordination_bonus_usd, 2)

    for code, s in sellers_data.items():
        if code != "23":
            s["comision_total_bs"] = s["comision_directa_bs"]
            s["comision_total_usd"] = s["comision_directa_usd"]

    sellers_list = list(sellers_data.values())
    if unassigned["transaction_count"] > 0:
        unassigned["ventas_totales_usd"] = max(0.0, round(
            unassigned["ventas_comerciales_contado_usd"] + unassigned["ventas_comerciales_credito_usd"] - unassigned["ventas_comerciales_devolucion_usd"], 2
        ))
        sellers_list.append(unassigned)

    # Totales de Liquidación
    total_contado_bs = round(sum(s["ventas_contado_bs"] for s in sellers_list), 2)
    total_cxc_bs = round(sum(s["cxc_cobradas_bs"] for s in sellers_list), 2)
    total_dev_bs = round(sum(s["devoluciones_bs"] for s in sellers_list), 2)
    total_base_bs = round(sum(s["base_neta_bs"] for s in sellers_list), 2)
    total_comisiones_bs = round(sum(s["comision_total_bs"] for s in sellers_list), 2)

    total_contado_usd = round(sum(s["ventas_contado_usd"] for s in sellers_list), 2)
    total_cxc_usd = round(sum(s["cxc_cobradas_usd"] for s in sellers_list), 2)
    total_dev_usd = round(sum(s["devoluciones_usd"] for s in sellers_list), 2)
    total_base_usd = round(sum(s["base_neta_usd"] for s in sellers_list), 2)
    total_comisiones_usd = round(sum(s["comision_total_usd"] for s in sellers_list), 2)

    # Detalle del Coordinador de Ventas (sin nombres personales)
    coordination_detail = {
        "title": "Coordinador de Ventas",
        "coordination_rate_pct": "1%",
        "team_members": [
            {
                "code": c,
                "name": sellers_data[c]["name"],
                "base_neta_bs": sellers_data[c]["base_neta_bs"],
                "base_neta_usd": sellers_data[c]["base_neta_usd"],
                "comision_coord_bs": round(sellers_data[c]["base_neta_bs"] * COORDINATION_RATE, 2),
                "comision_coord_usd": round(sellers_data[c]["base_neta_usd"] * COORDINATION_RATE, 2)
            } for c in COORDINATION_TEAM_CODES if c in sellers_data
        ],
        "team_base_bs": team_coordination_base_bs,
        "team_base_usd": team_coordination_base_usd,
        "coordination_bonus_bs": coordination_bonus_bs,
        "coordination_bonus_usd": coordination_bonus_usd
    }

    # Desempeño Comercial: Ranking y Total de Ventas en $ (Hoja GRAFICO DE VENTAS)
    total_empresa_ventas_usd = round(sum(s["ventas_totales_usd"] for s in sellers_list), 2)
    ranking_list = sorted(
        [
            {
                "code": s["code"],
                "name": s["name"],
                "is_office": s["is_office"],
                "ventas_contado_usd": s["ventas_comerciales_contado_usd"],
                "ventas_credito_usd": s["ventas_comerciales_credito_usd"],
                "devoluciones_usd": s["ventas_comerciales_devolucion_usd"],
                "ventas_totales_usd": s["ventas_totales_usd"],
                "participacion_pct": round((s["ventas_totales_usd"] / total_empresa_ventas_usd * 100), 2) if total_empresa_ventas_usd > 0 else 0.0
            } for s in sellers_list if (s["ventas_totales_usd"] > 0 or not s["is_office"])
        ],
        key=lambda x: x["ventas_totales_usd"],
        reverse=True
    )
    for idx, r in enumerate(ranking_list, 1):
        r["rank"] = idx

    return {
        "period": {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "label": f"{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}"
        },
        "sellers": sellers_list,
        "coordination_detail": coordination_detail,
        "sales_ranking": ranking_list,
        "totals": {
            # En Bolívares
            "total_ventas_contado_bs": total_contado_bs,
            "total_cxc_cobradas_bs": total_cxc_bs,
            "total_devoluciones_bs": total_dev_bs,
            "total_base_neta_bs": total_base_bs,
            "total_comisiones_a_pagar_bs": total_comisiones_bs,
            # En Dólares
            "total_ventas_contado_usd": total_contado_usd,
            "total_cxc_cobradas_usd": total_cxc_usd,
            "total_devoluciones_usd": total_dev_usd,
            "total_base_neta_usd": total_base_usd,
            "total_comisiones_a_pagar_usd": total_comisiones_usd,
            # Total Ventas Comerciales
            "total_ventas_comerciales_usd": total_empresa_ventas_usd
        }
    }
