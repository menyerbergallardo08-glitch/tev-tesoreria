import os, sys, datetime
from fastapi.testclient import TestClient

proj_dir = r'C:\Users\GATEWAY\Desktop\CLIENTES DE CONSULTORIA\TODO ELECTRICO VALENCIA\SISTEMA DE TESORERIA Y FLUJO DE CAJA'
sys.path.insert(0, proj_dir)

from main import app
from database import get_db, SessionLocal
from models import User, Transaction, DailyCashClose, TreasuryAccount
from auth import create_access_token

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Todo Eléctrico Valencia" in data["app"]

def test_login_and_roles():
    # Test valid login
    response = client.post("/api/auth/login", json={"username": "directivo", "password": "tev2026*"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "directivo"

    # Test invalid login returns 401 Unauthorized
    bad_res = client.post("/api/auth/login", json={"username": "directivo", "password": "wrongpassword"})
    assert bad_res.status_code in [400, 401]

def test_live_sales_and_duality():
    # Login as directivo
    login_res = client.post("/api/auth/login", json={"username": "directivo", "password": "tev2026*"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Factura Fiscal de Contado
    res1 = client.post("/api/sales/live", headers=headers, json={
        "date": str(datetime.date.today()),
        "doc_type": "FACTURA_FISCAL",
        "doc_number": "TEST-FAC-001",
        "client_name": "Cliente Prueba Fiscal",
        "client_rif": "J-12345678",
        "is_credit": False,
        "amount_original": 100.0,
        "currency": "USD",
        "account_id": 1,
        "pos_terminal": "",
        "description": "Venta de prueba fiscal"
    })
    assert res1.status_code == 200

    # 2. Nota de Entrega a Crédito (CxC)
    res2 = client.post("/api/sales/live", headers=headers, json={
        "date": str(datetime.date.today()),
        "doc_type": "NOTA_ENTREGA",
        "doc_number": "TEST-NE-001",
        "client_name": "Cliente Prueba Crédito",
        "client_rif": "V-98765432",
        "is_credit": True,
        "amount_original": 500.0,
        "currency": "USD",
        "description": "Despacho a crédito de prueba"
    })
    assert res2.status_code == 200
    credit_id = res2.json()["id"]

    # 3. Check receivables list
    rec_res = client.get("/api/receivables", headers=headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    rec_items = rec_data.get("items", rec_data) if isinstance(rec_data, dict) else rec_data
    assert any(r["id"] == credit_id for r in rec_items)

    # 4. Register Abono Parcial of $200 to that credit
    abono_res = client.post(f"/api/receivables/{credit_id}/abono", headers=headers, json={
        "date": str(datetime.date.today()),
        "amount_original": 200.0,
        "currency": "USD",
        "account_id": 1,
        "reference_number": "ABONO-REF-01",
        "description": "Primer abono de prueba"
    })
    assert abono_res.status_code == 200
    abono_data = abono_res.json()
    assert abono_data["remaining_balance_usd"] == 300.0
    assert abono_data["status"] == "PARCIALMENTE_PAGADO"

    # 5. Live Monitor check
    mon_res = client.get("/api/sales/live-monitor", headers=headers)
    assert mon_res.status_code == 200
    mon_data = mon_res.json()
    assert "sales" in mon_data
    assert "live_funds_expected" in mon_data

def test_daily_cash_close_summary():
    login_res = client.post("/api/auth/login", json={"username": "directivo", "password": "tev2026*"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    summary_res = client.get("/api/cash-close/summary", headers=headers)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert "sales_summary" in summary_data
    assert "collections_summary" in summary_data

if __name__ == "__main__":
    print("Running automated test suite against FastAPI & Supabase...")
    test_health_check()
    print("[+] test_health_check: PASSED")
    test_login_and_roles()
    print("[+] test_login_and_roles: PASSED")
    test_live_sales_and_duality()
    print("[+] test_live_sales_and_duality: PASSED")
    test_daily_cash_close_summary()
    print("[+] test_daily_cash_close_summary: PASSED")
    print("\n[OK] ALL 4 AUTOMATED TEST SUITES PASSED WITH 100% SUCCESS!")
