import os
import sys
import time
import datetime
from fastapi.testclient import TestClient

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from main import app
from database import SessionLocal
from models import User, Transaction, TreasuryAccount

client = TestClient(app)

def test_expense_with_seniat_retention_and_cash_flow():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == 'directivo').first()
        if not admin:
            admin = db.query(User).first()
        from core.security import create_access_token
        token = create_access_token({"sub": admin.username, "role": admin.role})
        headers = {"Authorization": f"Bearer {token}"}

        acc = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True, TreasuryAccount.currency == 'USD').first()
        assert acc is not None

        today_str = datetime.date.today().isoformat()
        current_month = today_str[:7]
        ts = int(time.time() * 1000)

        net_to_pay = 1020.0
        ret_amount = 140.0
        proof_num = f"{datetime.date.today().year}{datetime.date.today().month:02d}{str(ts)[-8:]}"

        payload = {
            "date": today_str,
            "movement_type": "EGRESO",
            "subtype": "PAGO_PROVEEDOR",
            "account_id": acc.id,
            "amount_original": net_to_pay,
            "currency": "USD",
            "exchange_rate": 1.0,
            "reference_number": f"REF-RET-{ts}",
            "beneficiary": f"Proveedor Cables Valencia #{ts}",
            "description": f"Pago Factura Cables con Retencion SENIAT [Total: 1160.00 | Ret IVA: 120.00 | Ret ISLR: 20.00 | Neto: {net_to_pay}]",
            "tax_retention_amount": ret_amount,
            "tax_retention_proof": proof_num
        }

        res_create = client.post("/api/transactions", json=payload, headers=headers)
        assert res_create.status_code == 200, f"Error creando egreso con retencion: {res_create.text}"
        tx_data = res_create.json()
        assert tx_data["success"] is True
        assert tx_data["amount_usd"] == net_to_pay

        # Validar en base de datos la persistencia de las retenciones
        saved_tx = db.query(Transaction).filter(Transaction.id == tx_data["id"]).first()
        assert saved_tx is not None
        assert saved_tx.tax_retention_amount == ret_amount
        assert saved_tx.tax_retention_proof == proof_num

        # Validar integración con el endpoint de Flujo de Caja
        res_cf = client.get(f"/api/dashboard/cash-flow?month={current_month}", headers=headers)
        assert res_cf.status_code == 200, f"Error en cash flow: {res_cf.text}"
        cf_data = res_cf.json()

        assert "tax_retentions_accumulated_usd" in cf_data
        assert "fiscal_reserve_seniat_usd" in cf_data
        assert "free_operational_cash_usd" in cf_data

        assert cf_data["tax_retentions_accumulated_usd"] >= ret_amount
        assert cf_data["fiscal_reserve_seniat_usd"] >= ret_amount
        expected_free_cash = round(cf_data["final_balance_usd"] - cf_data["fiscal_reserve_seniat_usd"], 2)
        assert cf_data["free_operational_cash_usd"] == expected_free_cash

    finally:
        db.close()
