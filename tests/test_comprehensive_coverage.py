import time
import datetime
import unittest
import unittest.mock
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import User, TreasuryAccount, Transaction, BudgetCategory
from core.config import MASTER_ADMIN_KEY

client = TestClient(app)

def test_full_routers_and_services_coverage():
    ts = int(time.time() * 1000)

    # 1. Login Master y Cajera
    res_master = client.post("/api/auth/login", json={"username": "master", "password": "master2026*"})
    assert res_master.status_code == 200
    token_master = res_master.json()["access_token"]
    h_master = {"Authorization": f"Bearer {token_master}"}

    res_caj = client.post("/api/auth/login", json={"username": "cajera1", "password": "caja12026*"})
    token_caj = res_caj.json()["access_token"] if res_caj.status_code == 200 else token_master
    h_caj = {"Authorization": f"Bearer {token_caj}"}

    # 2. Routers: Auth (Users, Change Password)
    res_users = client.get("/api/auth/users", headers=h_master)
    assert res_users.status_code == 200
    assert len(res_users.json()) >= 1

    res_new_user = client.post("/api/auth/users", json={
        "username": f"user_test_{ts}",
        "password": "pwd_test_2026*",
        "full_name": "Usuario Test Cobertura",
        "role": "cajera"
    }, headers=h_master)
    assert res_new_user.status_code == 200

    res_ch_pwd = client.post("/api/auth/change-password", json={
        "old_password": "master2026*",
        "new_password": "master2026*"
    }, headers=h_master)
    assert res_ch_pwd.status_code == 200

    # 3. Routers: Accounts (Crear cuenta, listar todas, actualizar)
    res_create_acc = client.post("/api/accounts", json={
        "name": f"Cuenta Test {ts}",
        "currency": "USD",
        "account_type": "BANCO",
        "initial_balance": 100.0,
        "only_income": False
    }, headers=h_master)
    assert res_create_acc.status_code == 200
    test_acc_id = res_create_acc.json()["id"]

    res_put_acc = client.put(f"/api/accounts/{test_acc_id}", json={
        "name": f"Cuenta Test Editada {ts}",
        "account_type": "Caja Operativa",
        "initial_balance": 150.0,
        "is_active": True
    }, headers=h_master)
    assert res_put_acc.status_code == 200

    res_acc_all = client.get("/api/accounts?all=true", headers=h_master)
    assert res_acc_all.status_code == 200

    # 4. Routers: Categories (Listar con mes, crear nueva partida, actualizar)
    import random
    rand_code = random.randint(1000, 9999)
    res_create_cat = client.post("/api/categories", json={
        "code": rand_code,
        "name": f"Partida Cobertura {rand_code}",
        "monthly_budget_usd": 300.0
    }, headers=h_master)
    assert res_create_cat.status_code == 200
    new_cat_id = res_create_cat.json()["id"]

    res_put_cat = client.put(f"/api/categories/{new_cat_id}", json={
        "monthly_budget_usd": 450.0,
        "is_active": True
    }, headers=h_master)
    assert res_put_cat.status_code == 200

    res_cats = client.get("/api/categories?month=2026-09&include_inactive=true", headers=h_master)
    assert res_cats.status_code == 200

    # 5. Routers: Sales (Crear, Void, Summary-today)
    res_sale = client.post("/api/sales", json={
        "date": "2026-09-18",
        "doc_type": "FACTURA_FISCAL",
        "doc_number": f"COV-FAC-{ts}",
        "client_name": "Cliente Cobertura",
        "amount_usd": 85.0,
        "payment_method": "EFECTIVO_USD",
        "account_id": test_acc_id
    }, headers=h_master)
    assert res_sale.status_code == 200
    sale_id = res_sale.json()["id"]

    res_summary = client.get("/api/sales/summary-today?date=2026-09-18", headers=h_master)
    assert res_summary.status_code == 200
    assert res_summary.json()["total_collected_usd"] >= 85.0

    res_void = client.post("/api/sales/void", json={
        "transaction_id": sale_id,
        "reason": "Error en digitación durante auditoría"
    }, headers=h_master)
    assert res_void.status_code == 200

    # 6. Routers: Expenses (Suppliers, Retention post-payment)
    res_supp = client.post("/api/expenses/suppliers", json={
        "name": f"Proveedor Cobertura {ts}",
        "rif": "J-99999999-1",
        "phone": "0414-9999999",
        "bank_details": "Banesco 0134"
    }, headers=h_master)
    assert res_supp.status_code == 200

    res_list_supp = client.get("/api/expenses/suppliers", headers=h_master)
    assert res_list_supp.status_code == 200

    res_exp = client.post("/api/expenses", json={
        "date": "2026-09-18",
        "category_id": 1,
        "account_id": test_acc_id,
        "amount_usd": 60.0,
        "currency": "USD",
        "subtype": "GASTO_OPERATIVO",
        "beneficiary": f"Beneficiario {ts}",
        "reference_number": f"EXP-COV-{ts}"
    }, headers=h_master)
    assert res_exp.status_code == 200
    exp_id = res_exp.json()["id"]

    res_ret = client.post(f"/api/expenses/{exp_id}/retention", json={
        "tax_retention_amount": 5.0,
        "tax_retention_proof": "2026-09-00000088"
    }, headers=h_master)
    assert res_ret.status_code == 200

    # 7. Routers: CxC (Listar pendientes por status)
    res_debts_all = client.get("/api/cxc/debts?status=ALL", headers=h_master)
    assert res_debts_all.status_code == 200
    res_debts_pen = client.get("/api/cxc/debts?status=PENDING", headers=h_master)
    assert res_debts_pen.status_code == 200
    res_debts_paid = client.get("/api/cxc/debts?status=PAID", headers=h_master)
    assert res_debts_paid.status_code == 200

    # 8. Routers: Cash Close (Listar y Crear)
    res_close_list = client.get("/api/cash-closes", headers=h_master)
    assert res_close_list.status_code == 200

    import random
    unique_day = random.randint(1, 28)
    unique_month = random.randint(1, 12)
    close_date_str = f"2029-{unique_month:02d}-{unique_day:02d}"
    res_create_close = client.post("/api/cash-closes", json={
        "date": close_date_str,
        "status": "CUADRADO",
        "profit_sales_total_usd": 150.0,
        "cash_usd_physical": 100.0,
        "pos_total_usd": 50.0,
        "bank_transfers_usd": 0.0,
        "cashea_usd": 0.0,
        "retentions_iva_usd": 0.0,
        "retentions_islr_usd": 0.0,
        "total_expected_usd": 150.0,
        "difference_usd": 0.0,
        "notes": "Cierre de prueba cobertura"
    }, headers=h_master)
    assert res_create_close.status_code in (200, 409)

    # 9. Routers: Audit
    res_audit = client.get("/api/audit/logs?limit=50", headers=h_master)
    assert res_audit.status_code == 200

    # 10. Routers: System (Health, BCV Rate, Backups, FIFO Prune, Content)
    res_health = client.get("/api/system/health")
    assert res_health.status_code == 200

    res_bcv = client.get("/api/system/bcv-rate")
    assert res_bcv.status_code == 200

    res_set_bcv = client.post("/api/system/bcv-rate", json={"rate": 880.50}, headers=h_master)
    assert res_set_bcv.status_code == 200

    # Generar backup determinístico y descargarlo/leer contenido
    res_bkp = client.post("/api/system/backup", headers=h_master)
    assert res_bkp.status_code == 200
    bkp_filename = res_bkp.json()["filename"]

    res_bkp_content = client.get(f"/api/system/backups/{bkp_filename}/content", headers=h_master)
    assert res_bkp_content.status_code == 200
    bkp_data = res_bkp_content.json()

    res_bkp_down = client.get(f"/api/system/backups/{bkp_filename}/download", headers=h_master)
    assert res_bkp_down.status_code == 200

    # Ejecutar poda FIFO desde el endpoint
    res_fifo = client.post("/api/system/backups/fifo-prune?max_count=14", headers=h_master)
    assert res_fifo.status_code == 200

    # Restaurar backup determinístico
    res_restore = client.post("/api/system/restore", json={
        "master_key": MASTER_ADMIN_KEY,
        "backup_data": bkp_data
    }, headers=h_master)
    assert res_restore.status_code == 200
    assert res_restore.json()["status"] == "RESTORE_SUCCESS"

    # Clave maestra errónea en restore
    res_restore_bad = client.post("/api/system/restore", json={
        "master_key": "CLAVE_INCORRECTA",
        "backup_data": bkp_data
    }, headers=h_master)
    assert res_restore_bad.status_code == 403

    # Clean-slate (Puesta a cero)
    res_clean = client.post("/api/system/clean-slate", json={
        "master_key": MASTER_ADMIN_KEY,
        "confirmation_phrase": "CONFIRMAR-PURGA-TEV"
    }, headers=h_master)
    assert res_clean.status_code == 200

    # Clean-slate con error de confirmación
    res_clean_bad = client.post("/api/system/clean-slate", json={
        "master_key": MASTER_ADMIN_KEY,
        "confirmation_phrase": "WRONG"
    }, headers=h_master)
    assert res_clean_bad.status_code == 400

    # Probar helpers S3 y funciones de backup_service directamente
    from services.backup_service import (
        get_s3_config,
        upload_to_s3_compatible,
        download_from_s3_compatible,
        delete_from_s3_compatible
    )
    with unittest.mock.patch.dict("os.environ", {
        "S3_ENDPOINT_URL": "http://minio:9000",
        "S3_ACCESS_KEY_ID": "test_access",
        "S3_SECRET_ACCESS_KEY": "test_secret",
        "S3_BUCKET": "test_bucket"
    }):
        cfg = get_s3_config()
        assert cfg is not None
        with unittest.mock.patch("boto3.client") as mock_boto:
            mock_client = unittest.mock.MagicMock()
            mock_boto.return_value = mock_client
            assert upload_to_s3_compatible("dummy.json", "dummy.json") is True
            assert download_from_s3_compatible("dummy.json", "dummy.json") is True
            assert delete_from_s3_compatible("dummy.json") is True

    # 13. Routers: Dashboard (Flujo de Caja Mensual, Anual y Diario)
    res_cf_aug = client.get("/api/dashboard/cash-flow?month=2026-08", headers=h_master)
    assert res_cf_aug.status_code == 200
    res_cf_dec = client.get("/api/dashboard/cash-flow?month=2026-12", headers=h_master)
    assert res_cf_dec.status_code == 200
    res_cf_annual = client.get("/api/dashboard/cash-flow-annual?year=2026", headers=h_master)
    assert res_cf_annual.status_code == 200
    assert len(res_cf_annual.json()["months"]) == 12
    res_cf_daily = client.get("/api/dashboard/cash-flow-daily?month=2026-08", headers=h_master)
    assert res_cf_daily.status_code == 200
    assert len(res_cf_daily.json()["days"]) == 31
    res_cf_daily_dec = client.get("/api/dashboard/cash-flow-daily?month=2026-12", headers=h_master)
    assert res_cf_daily_dec.status_code == 200
    res_bad_cf = client.get("/api/dashboard/cash-flow?month=bad-format", headers=h_master)
    assert res_bad_cf.status_code in [400, 422]


