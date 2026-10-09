import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import TreasuryAccount, AccountMonthlyBalance, Transaction, BudgetCategory, User
from core.security import require_roles

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard / Flujo de Caja"])


# -------------------------------------------------------------
# DEDICATED CASH FLOW ENDPOINTS (Flujo de Caja Mensual y Anual)
# -------------------------------------------------------------
@router.get("/cash-flow")
def get_cash_flow(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    try:
        year, m = map(int, month.split("-"))
        start_date = datetime.date(year, m, 1)
        if m == 12:
            end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de mes inválido. Use YYYY-MM.")

    accounts = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).all()

    avg_rate_rec = db.query(func.avg(Transaction.exchange_rate)).filter(
        Transaction.currency == "VES",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.status != "ANULADO"
    ).scalar()
    month_avg_rate = float(avg_rate_rec) if avg_rate_rec and avg_rate_rec > 0 else 756.71

    accounts_detail = []
    total_initial_usd = 0.0
    total_final_usd = 0.0

    total_usd_cash = 0.0
    total_ves_bank = 0.0
    total_usdt = 0.0

    for acc in accounts:
        m_rec = db.query(AccountMonthlyBalance).filter(
            AccountMonthlyBalance.account_id == acc.id,
            AccountMonthlyBalance.month == month
        ).first()
        init_bal = m_rec.initial_balance if m_rec else acc.initial_balance

        ingresos_orig = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.movement_type == "INGRESO",
            Transaction.subtype != "TRASPASO_ENTRADA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        egresos_orig = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.movement_type == "EGRESO",
            Transaction.subtype != "TRASPASO_SALIDA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        traspasos_in = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.subtype == "TRASPASO_ENTRADA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        traspasos_out = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.subtype == "TRASPASO_SALIDA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        final_orig = init_bal + ingresos_orig - egresos_orig + traspasos_in - traspasos_out

        if acc.currency == "USD":
            init_usd = init_bal
            final_usd = final_orig
            total_usd_cash += final_orig
        elif acc.currency == "USDT":
            init_usd = init_bal
            final_usd = final_orig
            total_usdt += final_orig
        else:
            init_usd = init_bal / month_avg_rate
            final_usd = final_orig / month_avg_rate
            total_ves_bank += final_orig

        total_initial_usd += init_usd
        total_final_usd += final_usd

        accounts_detail.append({
            "account_id": acc.id,
            "name": acc.name,
            "currency": acc.currency,
            "account_type": acc.account_type,
            "initial_balance": round(init_bal, 2),
            "inflows_orig": round(ingresos_orig, 2),
            "outflows_orig": round(egresos_orig, 2),
            "transfers_net_orig": round(traspasos_in - traspasos_out, 2),
            "final_balance": round(final_orig, 2),
            "initial_balance_usd": round(init_usd, 2),
            "final_balance_usd": round(final_usd, 2)
        })

    # Ingresos Operativos en USD
    ventas_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "INGRESO",
        Transaction.subtype == "VENTA_DIARIA",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    cobros_cxc_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "INGRESO",
        Transaction.subtype == "COBRO_CXC",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    otros_ingresos_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "INGRESO",
        Transaction.subtype.notin_(["VENTA_DIARIA", "COBRO_CXC", "TRASPASO_ENTRADA"]),
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    total_inflows_usd = ventas_usd + cobros_cxc_usd + otros_ingresos_usd

    # Egresos Operativos en USD (Desglose por partidas presupuestarias y proveedores)
    categories = db.query(BudgetCategory).filter(BudgetCategory.is_active == True).order_by(BudgetCategory.code).all()
    categories_breakdown = []
    total_gastos_op_usd = 0.0
    for cat in categories:
        cat_spent = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.category_id == cat.id,
            Transaction.movement_type == "EGRESO",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()
        total_gastos_op_usd += cat_spent
        if cat_spent > 0 or cat.monthly_budget_usd > 0:
            categories_breakdown.append({
                "code": cat.code,
                "name": cat.name,
                "spent_usd": round(cat_spent, 2)
            })

    pagos_prov_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "EGRESO",
        Transaction.subtype == "PAGO_PROVEEDOR",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    retiros_acc_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "EGRESO",
        Transaction.subtype == "RETIRO_ACCIONISTA",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    otros_egresos_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "EGRESO",
        Transaction.subtype.notin_(["GASTO_OPERATIVO", "PAGO_PROVEEDOR", "RETIRO_ACCIONISTA", "TRASPASO_SALIDA"]),
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    total_outflows_usd = total_gastos_op_usd + pagos_prov_usd + otros_egresos_usd

    # Diferencial Cambiario de Traspasos
    traspasos_out_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.subtype == "TRASPASO_SALIDA",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    traspasos_in_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.subtype == "TRASPASO_ENTRADA",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    fx_differential_usd = traspasos_in_usd - traspasos_out_usd

    net_operational_cash_flow = total_inflows_usd - total_outflows_usd
    net_total_cash_flow = net_operational_cash_flow + fx_differential_usd

    return {
        "month": month,
        "period_label": f"{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}",
        "initial_balance_usd": round(total_initial_usd, 2),
        "total_inflows_usd": round(total_inflows_usd, 2),
        "inflows_breakdown": {
            "ventas_usd": round(ventas_usd, 2),
            "cobros_cxc_usd": round(cobros_cxc_usd, 2),
            "otros_ingresos_usd": round(otros_ingresos_usd, 2)
        },
        "total_outflows_usd": round(total_outflows_usd, 2),
        "outflows_breakdown": {
            "gastos_operativos_usd": round(total_gastos_op_usd, 2),
            "pagos_proveedores_usd": round(pagos_prov_usd, 2),
            "retiros_accionistas_usd": round(retiros_acc_usd, 2),
            "otros_egresos_usd": round(otros_egresos_usd, 2),
            "categories": categories_breakdown
        },
        "fx_differential_usd": round(fx_differential_usd, 2),
        "net_operational_flow_usd": round(net_operational_cash_flow, 2),
        "net_cash_flow_usd": round(net_total_cash_flow, 2),
        "final_balance_usd": round(total_final_usd, 2),
        "currency_summary": {
            "usd_cash": round(total_usd_cash, 2),
            "ves_bank": round(total_ves_bank, 2),
            "usdt": round(total_usdt, 2),
            "rate_used": round(month_avg_rate, 2)
        },
        "accounts_detail": accounts_detail
    }


@router.get("/cash-flow-annual")
def get_annual_cash_flow(
    year: int = Query(2026),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    months_labels = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    matrix_data = []

    for idx, label in enumerate(months_labels, 1):
        m_str = f"{year}-{idx:02d}"
        start_d = datetime.date(year, idx, 1)
        if idx == 12:
            end_d = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_d = datetime.date(year, idx + 1, 1) - datetime.timedelta(days=1)

        # Ingresos
        ventas = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "INGRESO",
            Transaction.subtype == "VENTA_DIARIA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        cxc = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "INGRESO",
            Transaction.subtype == "COBRO_CXC",
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        otros_in = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "INGRESO",
            Transaction.subtype.notin_(["VENTA_DIARIA", "COBRO_CXC", "TRASPASO_ENTRADA"]),
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        # Egresos
        gastos = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "EGRESO",
            Transaction.subtype == "GASTO_OPERATIVO",
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        prov = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "EGRESO",
            Transaction.subtype == "PAGO_PROVEEDOR",
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        otros_out = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "EGRESO",
            Transaction.subtype.notin_(["GASTO_OPERATIVO", "PAGO_PROVEEDOR", "TRASPASO_SALIDA"]),
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        tot_in = ventas + cxc + otros_in
        tot_out = gastos + prov + otros_out
        net = tot_in - tot_out

        matrix_data.append({
            "month_index": idx,
            "month_label": label,
            "ventas": round(ventas, 2),
            "cxc": round(cxc, 2),
            "otros_in": round(otros_in, 2),
            "total_in": round(tot_in, 2),
            "gastos": round(gastos, 2),
            "prov": round(prov, 2),
            "otros_out": round(otros_out, 2),
            "total_out": round(tot_out, 2),
            "net": round(net, 2)
        })

    return {"year": year, "months": matrix_data}


@router.get("/cash-flow-daily")
def get_daily_cash_flow(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    year, m = map(int, month.split("-"))
    start_date = datetime.date(year, m, 1)
    if m == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)

    txs = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.status != "ANULADO"
    ).order_by(Transaction.date.asc()).all()

    days_map = {}
    cur_date = start_date
    while cur_date <= end_date:
        d_key = cur_date.isoformat()
        days_map[d_key] = {
            "date": d_key,
            "day_num": cur_date.day,
            "ventas": 0.0,
            "cxc": 0.0,
            "otros_in": 0.0,
            "total_in": 0.0,
            "gastos": 0.0,
            "prov": 0.0,
            "otros_out": 0.0,
            "total_out": 0.0,
            "net": 0.0,
            "count": 0
        }
        cur_date += datetime.timedelta(days=1)

    tot_ventas = 0.0
    tot_cxc = 0.0
    tot_otros_in = 0.0
    tot_gastos = 0.0
    tot_prov = 0.0
    tot_otros_out = 0.0

    for t in txs:
        d_str = t.date.isoformat()
        if d_str in days_map:
            days_map[d_str]["count"] += 1
            if t.movement_type == "INGRESO":
                if t.subtype == "VENTA_DIARIA":
                    days_map[d_str]["ventas"] += t.amount_usd
                    tot_ventas += t.amount_usd
                elif t.subtype == "COBRO_CXC":
                    days_map[d_str]["cxc"] += t.amount_usd
                    tot_cxc += t.amount_usd
                elif t.subtype != "TRASPASO_ENTRADA":
                    days_map[d_str]["otros_in"] += t.amount_usd
                    tot_otros_in += t.amount_usd
            elif t.movement_type == "EGRESO":
                if t.subtype == "GASTO_OPERATIVO":
                    days_map[d_str]["gastos"] += t.amount_usd
                    tot_gastos += t.amount_usd
                elif t.subtype == "PAGO_PROVEEDOR":
                    days_map[d_str]["prov"] += t.amount_usd
                    tot_prov += t.amount_usd
                elif t.subtype != "TRASPASO_SALIDA":
                    days_map[d_str]["otros_out"] += t.amount_usd
                    tot_otros_out += t.amount_usd

    result = []
    for d_str, val in sorted(days_map.items()):
        val["ventas"] = round(val["ventas"], 2)
        val["cxc"] = round(val["cxc"], 2)
        val["otros_in"] = round(val["otros_in"], 2)
        val["total_in"] = round(val["ventas"] + val["cxc"] + val["otros_in"], 2)

        val["gastos"] = round(val["gastos"], 2)
        val["prov"] = round(val["prov"], 2)
        val["otros_out"] = round(val["otros_out"], 2)
        val["total_out"] = round(val["gastos"] + val["prov"] + val["otros_out"], 2)

        val["net"] = round(val["total_in"] - val["total_out"], 2)
        result.append(val)

    tot_in_final = tot_ventas + tot_cxc + tot_otros_in
    tot_out_final = tot_gastos + tot_prov + tot_otros_out
    totals = {
        "ventas": round(tot_ventas, 2),
        "cxc": round(tot_cxc, 2),
        "otros_in": round(tot_otros_in, 2),
        "total_in": round(tot_in_final, 2),
        "gastos": round(tot_gastos, 2),
        "prov": round(tot_prov, 2),
        "otros_out": round(tot_otros_out, 2),
        "total_out": round(tot_out_final, 2),
        "net": round(tot_in_final - tot_out_final, 2)
    }

    return {"month": month, "days": result, "totals": totals}
