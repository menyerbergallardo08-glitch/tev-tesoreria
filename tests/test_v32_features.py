import os
import sys
import time
from fastapi.testclient import TestClient

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from main import app
from database import SessionLocal
from models import User, Transaction, TreasuryAccount

client = TestClient(app)

def test_suppliers_and_v32_features():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == 'directivo').first()
        if not admin:
            admin = db.query(User).first()
        from core.security import create_access_token
        token = create_access_token({"sub": admin.username, "role": admin.role})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test Suppliers
        res_list = client.get("/api/suppliers", headers=headers)
        assert res_list.status_code == 200

        ts = int(time.time() * 1000)
        res_create = client.post("/api/suppliers", json={
            "name": f"Proveedor Test {ts}",
            "rif": f"J-{ts % 100000000}-0",
            "phone": "0412-0000000",
            "bank_details": "Banesco 0134"
        }, headers=headers)
        assert res_create.status_code == 200
        sup_id = res_create.json()["id"]

        res_update = client.put(f"/api/suppliers/{sup_id}", json={
            "name": f"Proveedor Modificado {ts}",
            "phone": "0424-9999999"
        }, headers=headers)
        assert res_update.status_code == 200

        res_del = client.delete(f"/api/suppliers/{sup_id}", headers=headers)
        assert res_del.status_code == 200

        # 2. Test Expenses List
        res_exp_list = client.get("/api/expenses", headers=headers)
        assert res_exp_list.status_code == 200

        # 3. Test Transactions Edit / Cancel
        tx = db.query(Transaction).filter(Transaction.movement_type == 'EGRESO', Transaction.status != 'ANULADO').first()
        if tx:
            res_patch = client.patch(f"/api/transactions/{tx.id}", json={
                "beneficiary": "Beneficiario Ajustado Test",
                "description": "Ajuste de error de dedo test"
            }, headers=headers)
            assert res_patch.status_code == 200

        # 4. Test CxC Retención y Cruce NC
        cxc = db.query(Transaction).filter(Transaction.is_credit == True, Transaction.credit_balance_pending_usd > 1.0, Transaction.status != 'ANULADO').first()
        if cxc:
            res_ret = client.post("/api/cxc/payments", json={
                "transaction_id": cxc.id,
                "amount_usd": 0.50,
                "payment_type": "RETENCION",
                "retention_type": "IVA_75",
                "retention_proof": "20261000001234",
                "description": "Prueba retencion SENIAT"
            }, headers=headers)
            assert res_ret.status_code == 200

            res_nc = client.post("/api/cxc/payments", json={
                "transaction_id": cxc.id,
                "amount_usd": 0.50,
                "payment_type": "NOTA_CREDITO",
                "credit_note_ref": "NC-TEST-01",
                "description": "Prueba cruce NC"
            }, headers=headers)
            assert res_nc.status_code == 200

        # 5. Test Sales with USDT and NOTA_CREDITO
        res_usdt = client.post("/api/sales", json={
            "date": "2026-09-17",
            "doc_type": "NOTA_ENTREGA",
            "doc_number": f"SALE-USDT-{ts}",
            "client_name": "Cliente Binance",
            "amount_usd": 50.0,
            "payment_method": "USDT",
            "is_credit": False
        }, headers=headers)
        assert res_usdt.status_code == 200

        res_sale_nc = client.post("/api/sales", json={
            "date": "2026-09-17",
            "doc_type": "NOTA_ENTREGA",
            "doc_number": f"SALE-NC-{ts}",
            "client_name": "Cliente Saldo Favor",
            "amount_usd": 30.0,
            "payment_method": "NOTA_CREDITO",
            "reference_number": "NC-SALDO-09",
            "is_credit": False
        }, headers=headers)
        assert res_sale_nc.status_code == 200

        # 6. Test Director KPIs with CxC mix, DSO, and Supplier DPO
        # Create an expense with invoice_date
        from models.budget import BudgetCategory
        acc = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).first()
        cat = db.query(BudgetCategory).first()
        res_exp = client.post("/api/expenses", json={
            "date": "2026-10-20",
            "invoice_date": "2026-10-10",
            "category_id": cat.id if cat else 1,
            "account_id": acc.id if acc else 1,
            "amount_usd": 150.0,
            "currency": "USD",
            "subtype": "PAGO_PROVEEDOR",
            "beneficiary": f"Proveedor Test DPO {ts}",
            "description": "Pago factura a 10 dias"
        }, headers=headers)
        assert res_exp.status_code == 200

        res_dir = client.get("/api/dashboard/director-kpis?month=2026-10", headers=headers)
        assert res_dir.status_code == 200
        data_dir = res_dir.json()
        assert "cxc_kpi" in data_dir
        assert "currency_mix" in data_dir["cxc_kpi"]
        assert "avg_dso_days" in data_dir["cxc_kpi"]
        assert "prior_months_usd" in data_dir["cxc_kpi"]
        assert "supplier_dpo_kpi" in data_dir
        assert "avg_dpo_days" in data_dir["supplier_dpo_kpi"]
        assert data_dir["supplier_dpo_kpi"]["avg_dpo_days"] >= 0.0

        # 7. Test Cajera Role Allowed to Update BCV Rate
        cajera_user = db.query(User).filter(User.role == 'cajera').first()
        if cajera_user:
            cajera_token = create_access_token({"sub": cajera_user.username, "role": "cajera"})
            cajera_headers = {"Authorization": f"Bearer {cajera_token}"}
            res_bcv = client.post("/api/system/bcv-rate", json={"rate": 885.50}, headers=cajera_headers)
            assert res_bcv.status_code == 200
            assert res_bcv.json()["rate"] == 885.50

    finally:
        db.close()
