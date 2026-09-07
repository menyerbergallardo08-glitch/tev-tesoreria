from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "Todo Eléctrico Valencia" in response.text

def test_login_success():
    # Login Cajera 1
    res = client.post("/api/auth/login", json={"username": "cajera1", "password": "caja12026*"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "cajera"

    # Login Administradora
    res_admin = client.post("/api/auth/login", json={"username": "administradora", "password": "admin2026*"})
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert data_admin["user"]["role"] == "administradora"

    # Login Directivo
    res_dir = client.post("/api/auth/login", json={"username": "directivo", "password": "tev2026*"})
    assert res_dir.status_code == 200
    assert res_dir.json()["user"]["role"] == "directivo"

def test_accounts_and_categories():
    res_login = client.post("/api/auth/login", json={"username": "administradora", "password": "admin2026*"})
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Accounts
    res_acc = client.get("/api/accounts", headers=headers)
    assert res_acc.status_code == 200
    accounts = res_acc.json()
    assert len(accounts) >= 5
    currencies = {a["currency"] for a in accounts}
    assert "USD" in currencies
    assert "VES" in currencies
    assert "USDT" in currencies

    # Categories
    res_cat = client.get("/api/categories?month=2026-08", headers=headers)
    assert res_cat.status_code == 200
    cats = res_cat.json()
    assert len(cats) >= 12
    total_spent = sum(c["spent_usd"] for c in cats)
    # Debe ser $16,161.21 importado del Excel de Agosto
    assert abs(total_spent - 16161.21) < 0.1

def test_anti_error_validations():
    res_login = client.post("/api/auth/login", json={"username": "cajera1", "password": "caja12026*"})
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Gasto operativo sin categoría debe fallar
    res_fail_cat = client.post("/api/transactions", headers=headers, json={
        "date": "2026-09-07",
        "movement_type": "EGRESO",
        "subtype": "GASTO_OPERATIVO",
        "account_id": 1,
        "amount_original": 50.0,
        "currency": "USD",
        "exchange_rate": 1.0,
        "category_id": None
    })
    assert res_fail_cat.status_code == 400

    # 2. Monto cero o negativo debe fallar
    res_fail_amt = client.post("/api/transactions", headers=headers, json={
        "date": "2026-09-07",
        "movement_type": "EGRESO",
        "subtype": "GASTO_OPERATIVO",
        "account_id": 1,
        "category_id": 1,
        "amount_original": -10.0,
        "currency": "USD"
    })
    assert res_fail_amt.status_code == 400

def test_transaction_lifecycle_and_verification():
    # Cajera registra
    res_cajera = client.post("/api/auth/login", json={"username": "cajera2", "password": "caja22026*"})
    token_cajera = res_cajera.json()["access_token"]

    import time
    ref_test = f"REF-TEST-{int(time.time())}"
    tx_payload = {
        "date": "2026-09-07",
        "movement_type": "EGRESO",
        "subtype": "GASTO_OPERATIVO",
        "account_id": 2, # Banco Banesco VES
        "category_id": 4, # Servicios
        "amount_original": 7567.10,
        "currency": "VES",
        "exchange_rate": 756.71,
        "reference_number": ref_test,
        "beneficiary": "Corpoelec Valencia",
        "description": "Pago factura de luz sede principal"
    }

    res_create = client.post("/api/transactions", headers={"Authorization": f"Bearer {token_cajera}"}, json=tx_payload)
    assert res_create.status_code == 200
    tx_data = res_create.json()
    assert tx_data["success"] is True
    tx_id = tx_data["id"]
    assert abs(tx_data["amount_usd"] - 10.0) < 0.05

    # Intentar registrar la misma referencia en la misma cuenta debe fallar (Anti-duplicado)
    res_dup = client.post("/api/transactions", headers={"Authorization": f"Bearer {token_cajera}"}, json=tx_payload)
    assert res_dup.status_code == 400
    assert "Alerta de Duplicado" in res_dup.json()["detail"]

    # Administradora verifica el comprobante
    res_admin = client.post("/api/auth/login", json={"username": "administradora", "password": "admin2026*"})
    token_admin = res_admin.json()["access_token"]

    res_verify = client.patch(f"/api/transactions/{tx_id}/verify", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_verify.status_code == 200

def test_transfer_and_cash_flows():
    res_cajera = client.post("/api/auth/login", json={"username": "cajera1", "password": "caja12026*"})
    token_cajera = res_cajera.json()["access_token"]

    # Probar transferencia doble partida (ej: Caja Principal USD -> Banesco VES por cambio de divisa)
    import time
    ref_xfer = f"XFER-{int(time.time())}"
    transfer_payload = {
        "date": "2026-08-15",
        "origin_account_id": 1, # Caja USD
        "destination_account_id": 2,   # Banesco VES
        "amount_origin": 100.0,
        "amount_destination": 75000.0,
        "exchange_rate": 750.0,
        "reference_number": ref_xfer,
        "description": "Venta de 100 USD para pago de nómina bancaria"
    }
    res_xfer = client.post("/api/transactions/transfer", headers={"Authorization": f"Bearer {token_cajera}"}, json=transfer_payload)
    assert res_xfer.status_code == 200
    data_xfer = res_xfer.json()
    assert data_xfer["success"] is True
    assert "out_id" in data_xfer
    assert "in_id" in data_xfer

    # Cajera no puede ver Flujo de Caja (403 Forbidden)
    res_cf_cajera = client.get("/api/dashboard/cash-flow?month=2026-08", headers={"Authorization": f"Bearer {token_cajera}"})
    assert res_cf_cajera.status_code == 403

    # Administradora sí puede ver Flujo de Caja Mensual
    res_admin = client.post("/api/auth/login", json={"username": "administradora", "password": "admin2026*"})
    token_admin = res_admin.json()["access_token"]

    res_cf = client.get("/api/dashboard/cash-flow?month=2026-08", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_cf.status_code == 200
    cf_data = res_cf.json()
    assert "accounts_detail" in cf_data
    assert "total_outflows_usd" in cf_data
    assert "initial_balance_usd" in cf_data
    assert "currency_summary" in cf_data

    # Probar endpoint Flujo de Caja Anual
    res_ann = client.get("/api/dashboard/cash-flow-annual?year=2026", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_ann.status_code == 200
    ann_data = res_ann.json()
    assert len(ann_data["months"]) == 12

    # Probar endpoint Flujo de Caja Diario
    res_daily = client.get("/api/dashboard/cash-flow-daily?month=2026-08", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_daily.status_code == 200
    daily_data = res_daily.json()
    assert "days" in daily_data
    assert "totals" in daily_data
    assert len(daily_data["days"]) >= 28

    # Probar creación de nueva partida presupuestaria
    import time
    code_test = int(time.time()) % 10000 + 100
    cat_payload = {
        "code": code_test,
        "name": f"Partida Test {code_test}",
        "monthly_budget_usd": 350.0
    }
    res_cat = client.post("/api/categories", headers={"Authorization": f"Bearer {token_admin}"}, json=cat_payload)
    assert res_cat.status_code == 200
    assert res_cat.json()["name"] == f"Partida Test {code_test}"

def test_user_management_and_role_security():
    # Cajera no puede listar usuarios (403)
    res_cajera = client.post("/api/auth/login", json={"username": "cajera1", "password": "caja12026*"})
    token_cajera = res_cajera.json()["access_token"]
    res_users_cajera = client.get("/api/users", headers={"Authorization": f"Bearer {token_cajera}"})
    assert res_users_cajera.status_code == 403

    # Administradora tampoco puede gestionar usuarios (403)
    res_admin = client.post("/api/auth/login", json={"username": "administradora", "password": "admin2026*"})
    token_admin = res_admin.json()["access_token"]
    res_users_admin = client.get("/api/users", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_users_admin.status_code == 403

    # Directivo sí tiene acceso completo a gestionar usuarios
    res_dir = client.post("/api/auth/login", json={"username": "directivo", "password": "tev2026*"})
    token_dir = res_dir.json()["access_token"]
    res_users_dir = client.get("/api/users", headers={"Authorization": f"Bearer {token_dir}"})
    assert res_users_dir.status_code == 200
    users = res_users_dir.json()
    assert len(users) >= 4

def test_accounts_crud_and_excel_import():
    res_dir = client.post("/api/auth/login", json={"username": "directivo", "password": "tev2026*"})
    token_dir = res_dir.json()["access_token"]

    # 1. Crear nueva cuenta dinámica
    new_acc_payload = {
        "name": "Punto Bancamiga VES",
        "currency": "VES",
        "account_type": "Banco",
        "initial_balance": 1500.0
    }
    res_acc = client.post("/api/accounts", headers={"Authorization": f"Bearer {token_dir}"}, json=new_acc_payload)
    assert res_acc.status_code == 200
    acc_data = res_acc.json()
    assert acc_data["name"] == "Punto Bancamiga VES"
    acc_id = acc_data["id"]

    # 2. Editar cuenta dinámica
    res_up = client.put(f"/api/accounts/{acc_id}", headers={"Authorization": f"Bearer {token_dir}"}, json={"name": "Punto Bancamiga Principal"})
    assert res_up.status_code == 200
    assert res_up.json()["name"] == "Punto Bancamiga Principal"

    # 3. Probar subida de archivo Excel
    import os
    excel_sample = "CONTROL DE GASTOS 08 AGOSTO.xlsx"
    if os.path.exists(excel_sample):
        with open(excel_sample, "rb") as f:
            files = {"file": (excel_sample, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            res_import = client.post("/api/import/excel", headers={"Authorization": f"Bearer {token_dir}"}, files=files)
            assert res_import.status_code == 200
            import_data = res_import.json()
            assert import_data["success"] is True
            assert import_data["imported_count"] > 0

    # 4. Probar vaciado de transacciones para empezar en blanco
    res_clear = client.post("/api/admin/clear-transactions", headers={"Authorization": f"Bearer {token_dir}"})
    assert res_clear.status_code == 200
    assert res_clear.json()["success"] is True
    assert res_clear.json()["count_deleted"] >= 0

if __name__ == "__main__":
    print("Corriendo pruebas unitarias...")
    test_root_index()
    print("[OK] test_root_index paso")
    test_login_success()
    print("[OK] test_login_success paso")
    test_accounts_and_categories()
    print("[OK] test_accounts_and_categories paso")
    test_anti_error_validations()
    print("[OK] test_anti_error_validations paso")
    test_transaction_lifecycle_and_verification()
    print("[OK] test_transaction_lifecycle_and_verification paso")
    test_transfer_and_cash_flows()
    print("[OK] test_transfer_and_cash_flows paso")
    test_user_management_and_role_security()
    print("[OK] test_user_management_and_role_security paso")
    test_accounts_crud_and_excel_import()
    print("[OK] test_accounts_crud_and_excel_import paso")
    print("TODAS LAS PRUEBAS PASARON EXITOSAMENTE (100%)!")
