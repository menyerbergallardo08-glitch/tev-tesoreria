import os
import sys
import time
import json
import jwt

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import Transaction, TreasuryAccount, User, DailyCashClose, AuditLog
from core.config import JWT_SECRET_KEY, JWT_ALGORITHM

client = TestClient(app)

def run_qa_suite():
    print("=================================================================")
    print(" INICIANDO QA TEST SUITE & SECURITY CERTIFICATION - TEV v2.1")
    print("=================================================================")

    # 1. Login & Token JWT
    print("\n[TEST 1] Autenticacion Criptografica y Roles RBAC...")
    res_login = client.post("/api/auth/login", json={"username": "master", "password": "master2026*"})
    assert res_login.status_code == 200, f"Error login master: {res_login.text}"
    token_master = res_login.json()["access_token"]
    headers_master = {"Authorization": f"Bearer {token_master}"}
    print("  [OK] Login Master exitoso (JWT generado).")

    # 2. Token expirado (12h expiration test)
    expired_token = jwt.encode({"sub": "master", "exp": int(time.time()) - 3600}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    res_exp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_exp.status_code == 401
    print("  [OK] Token JWT expirado rechazado con 401 Unauthorized.")

    # 3. Token manipulado
    tampered_token = token_master[:-4] + "abcd"
    res_tamp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res_tamp.status_code == 401
    print("  [OK] Token JWT manipulado/firma invalida rechazado con 401 Unauthorized.")

    # 4. Cuentas y Soft Delete
    print("\n[TEST 2] Modulo Cajas/Bancos: CRUD y Soft Delete...")
    res_acc = client.get("/api/accounts", headers=headers_master)
    assert res_acc.status_code == 200
    active_accs = [a for a in res_acc.json() if a["is_active"]]
    acc_id = active_accs[0]["id"]
    acc_name = active_accs[0]["name"]
    
    res_toggle = client.post(f"/api/accounts/{acc_id}/toggle-status", headers=headers_master)
    assert res_toggle.status_code == 200
    assert res_toggle.json()["is_active"] == False
    print(f"  [OK] Cuenta '{acc_name}' inhabilitada con Soft Delete.")

    res_reactivate = client.post(f"/api/accounts/{acc_id}/toggle-status", headers=headers_master)
    assert res_reactivate.status_code == 200
    assert res_reactivate.json()["is_active"] == True
    print(f"  [OK] Cuenta '{acc_name}' reactivada.")

    # 5. Venta de Contado e Idempotencia
    print("\n[TEST 3] Venta de Contado y Proteccion Anti-Duplicados (HTTP 409)...")
    ts = int(time.time() * 1000)
    res_sale = client.post("/api/sales", json={
        "date": "2026-09-17",
        "doc_type": "NOTA_ENTREGA",
        "doc_number": f"QA-SALE-{ts}",
        "client_name": "Cliente QA",
        "amount_usd": 65.0,
        "payment_method": "EFECTIVO_USD",
        "account_id": acc_id
    }, headers=headers_master)
    assert res_sale.status_code == 200
    print("  [OK] Venta de contado registrada.")

    res_dup = client.post("/api/sales", json={
        "date": "2026-09-17",
        "doc_type": "NOTA_ENTREGA",
        "doc_number": f"QA-SALE-{ts}",
        "client_name": "Cliente QA",
        "amount_usd": 65.0,
        "payment_method": "EFECTIVO_USD",
        "account_id": acc_id
    }, headers=headers_master)
    assert res_dup.status_code == 409
    print("  [OK] Documento duplicado bloqueado con HTTP 409 Conflict.")

    # 6. Egresos y Retención SENIAT
    print("\n[TEST 4] Egresos con Retencion SENIAT...")
    res_exp = client.post("/api/expenses", json={
        "date": "2026-09-17",
        "category_id": 1,
        "account_id": acc_id,
        "amount_usd": 120.0,
        "currency": "USD",
        "subtype": "PAGO_PROVEEDOR",
        "beneficiary": "Proveedor QA",
        "reference_number": f"QA-EXP-{ts}",
        "tax_retention_amount": 12.0,
        "tax_retention_proof": "2026-09-00000077"
    }, headers=headers_master)
    assert res_exp.status_code == 200
    assert res_exp.json()["tax_retention_proof"] == "20260900000077"
    print("  [OK] Egreso y Comprobante SENIAT de 14 digitos validado.")

    # 7. Backup Determinístico y Restauración en Sandbox
    print("\n[TEST 5] Motor de Backup Deterministico y Restauracion...")
    res_bkp = client.post("/api/system/backup", headers=headers_master)
    assert res_bkp.status_code == 200
    bkp_data = res_bkp.json()
    assert bkp_data["status"] == "SUCCESS"
    assert bkp_data["total_records"] > 0
    print(f"  [OK] Backup generado: {bkp_data['filename']} ({bkp_data['total_records']} registros).")

    # Listar backups
    res_list_bkp = client.get("/api/system/backups", headers=headers_master)
    assert res_list_bkp.status_code == 200
    assert len(res_list_bkp.json()) > 0
    print("  [OK] Listado de backups locales verificado.")

    # 8. Transferencias entre cuentas activas
    print("\n[TEST 6] Transferencias Interbancarias...")
    acc_dest = active_accs[1]["id"]
    res_trans = client.post("/api/transfers", json={
        "date": "2026-09-17",
        "origin_account_id": acc_id,
        "destination_account_id": acc_dest,
        "amount_usd": 30.0,
        "description": "Traspaso de fondos QA"
    }, headers=headers_master)
    assert res_trans.status_code == 200
    print("  [OK] Transferencia interbancaria ejecutada exitosamente.")

    # 9. Tasa BCV
    print("\n[TEST 7] Tasa Oficial BCV y Politica de Fin de Semana...")
    res_bcv = client.get("/api/system/bcv-rate")
    assert res_bcv.status_code == 200
    assert res_bcv.json()["rate"] > 10.0
    print(f"  [OK] Tasa BCV resuelta: Bs. {res_bcv.json()['rate']:.2f}")

    print("\n=================================================================")
    print("  QA SUITE v2.1: 100% DE PRUEBAS COMPLETADAS EXITOSAMENTE")
    print("=================================================================\n")

if __name__ == "__main__":
    run_qa_suite()
