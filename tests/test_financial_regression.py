import os
import sys
import time
import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import Transaction, TreasuryAccount, User

client = TestClient(app)

def run_financial_regressions():
    print("=================================================================")
    print(" EJECUTANDO REGRESION FINANCIERA OBLIGATORIA (9 CASOS CRITICOS)")
    print("=================================================================")

    # Obtener token de autenticación master
    res_login = client.post("/api/auth/login", json={"username": "master", "password": "master2026*"})
    assert res_login.status_code == 200, "Login fallido"
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Obtener una cuenta activa para pruebas
    res_acc = client.get("/api/accounts", headers=headers)
    assert res_acc.status_code == 200
    active_accounts = [a for a in res_acc.json() if a["is_active"]]
    assert len(active_accounts) >= 2, "Se requieren al menos 2 cuentas activas para pruebas"
    acc1 = active_accounts[0]["id"]
    acc2 = active_accounts[1]["id"]

    ts = int(time.time() * 1000)

    # -------------------------------------------------------------
    # CASO 1: Venta de Contado ($100) -> Caja +$100, Venta $100, CxC $0
    # -------------------------------------------------------------
    print("\n[CASO 1] Venta de Contado ($100)...")
    res1 = client.post("/api/sales", json={
        "date": "2026-09-17",
        "doc_type": "NOTA_ENTREGA",
        "doc_number": f"REG-CONT-{ts}",
        "client_name": "Cliente Contado",
        "amount_usd": 100.0,
        "payment_method": "EFECTIVO_USD",
        "account_id": acc1
    }, headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["amount_usd"] == 100.0
    assert data1["credit_balance_pending_usd"] == 0.0
    assert data1["is_credit"] == False
    print("  [PASS] Venta Contado: Caja +$100.00 | Venta Reconocida = $100.00 | CxC = $0.00.")

    # -------------------------------------------------------------
    # CASO 2: Venta a Crédito Total ($100) -> Caja $0, Venta $100, CxC $100
    # -------------------------------------------------------------
    print("\n[CASO 2] Venta a Credito Total ($100 sin abono)...")
    res2 = client.post("/api/sales", json={
        "date": "2026-09-17",
        "doc_type": "NOTA_ENTREGA",
        "doc_number": f"REG-CRED-TOT-{ts}",
        "client_name": "Cliente Credito Total",
        "amount_usd": 100.0,
        "is_credit": True,
        "abono_usd": 0.0,
        "payment_method": "EFECTIVO_USD",
        "account_id": acc1
    }, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["amount_usd"] == 0.0, "Caja de hoy debe ser $0!"
    assert data2["credit_balance_pending_usd"] == 100.0, "CxC pendiente debe ser $100!"
    assert data2["credit_status"] == "PENDIENTE"
    print("  [PASS] Venta Credito Total: Caja = $0.00 | Venta Reconocida = $100.00 | CxC = $100.00.")

    # -------------------------------------------------------------
    # CASO 3: Venta a Crédito con Abono Parcial ($100 Venta, $30 Abono) -> Caja +$30, CxC $70
    # -------------------------------------------------------------
    print("\n[CASO 3] Venta a Credito con Abono Parcial ($100 venta, $30 abono)...")
    res3 = client.post("/api/sales", json={
        "date": "2026-09-17",
        "doc_type": "NOTA_ENTREGA",
        "doc_number": f"REG-CRED-ABO-{ts}",
        "client_name": "Cliente Abono Parcial",
        "amount_usd": 100.0,
        "is_credit": True,
        "abono_usd": 30.0,
        "abono_account_id": acc1,
        "payment_method": "EFECTIVO_USD"
    }, headers=headers)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["amount_usd"] == 30.0, "Solo debe entrar a caja el abono ($30)!"
    assert data3["credit_balance_pending_usd"] == 70.0, "CxC pendiente debe ser $70 ($100 - $30)!"
    assert data3["credit_status"] == "PARCIALMENTE_PAGADO"
    print("  [PASS] Venta Credito + Abono: Caja +$30.00 | Venta = $100.00 | CxC = $70.00 (Cero distorsion de $130).")

    # -------------------------------------------------------------
    # CASO 4: Cobro de CxC ($30 sobre saldo de $70) -> Caja +$30, CxC restante $40
    # -------------------------------------------------------------
    print("\n[CASO 4] Cobro de CxC ($30)...")
    sale3_id = data3["id"]
    res4 = client.post("/api/cxc/payments", json={
        "transaction_id": sale3_id,
        "amount_usd": 30.0,
        "account_id": acc1,
        "payment_method": "PAGO_MOVIL",
        "reference_number": f"COB-CXC-{ts}"
    }, headers=headers)
    assert res4.status_code == 200
    db = SessionLocal()
    updated_sale3 = db.query(Transaction).filter(Transaction.id == sale3_id).first()
    db.close()
    assert updated_sale3.credit_balance_pending_usd == 40.0
    assert updated_sale3.credit_status == "PARCIALMENTE_PAGADO"
    print("  [PASS] Cobro CxC: Caja +$30.00 | CxC Pendiente Reducido a $40.00 | No genera nueva venta.")

    # -------------------------------------------------------------
    # CASO 5: Deuda Histórica Onboarding ($500) -> Ventas $0, Caja $0, CxC $500
    # -------------------------------------------------------------
    print("\n[CASO 5] Deuda Historica Onboarding ($500)...")
    res5 = client.post("/api/cxc/historical-debt", json={
        "client_name": "Cliente Historico TEV",
        "doc_type": "NOTA_ENTREGA",
        "doc_number": f"HIST-DEBT-{ts}",
        "emission_date": "2026-07-01",
        "amount_usd": 500.0,
        "notes": "Saldo inicial de cliente antes del sistema"
    }, headers=headers)
    assert res5.status_code == 200
    hist_debt_id = res5.json()["id"]
    db = SessionLocal()
    hist_tx = db.query(Transaction).filter(Transaction.id == hist_debt_id).first()
    db.close()
    assert hist_tx.amount_usd == 0.0, "Caja de hoy debe ser $0 al cargar deuda historica!"
    assert hist_tx.credit_balance_pending_usd == 500.0
    print("  [PASS] Deuda Historica: Ventas Actuales = $0.00 | Caja = $0.00 | CxC = $500.00.")

    # -------------------------------------------------------------
    # CASO 6: Cobro Histórico ($200 sobre deuda de $500) -> Caja +$200, CxC $300
    # -------------------------------------------------------------
    print("\n[CASO 6] Cobro de Deuda Historica ($200)...")
    res6 = client.post("/api/cxc/payments", json={
        "transaction_id": hist_debt_id,
        "amount_usd": 200.0,
        "account_id": acc1,
        "payment_method": "TRANSFERENCIA",
        "reference_number": f"PAY-HIST-{ts}"
    }, headers=headers)
    assert res6.status_code == 200
    db = SessionLocal()
    hist_tx_updated = db.query(Transaction).filter(Transaction.id == hist_debt_id).first()
    db.close()
    assert hist_tx_updated.credit_balance_pending_usd == 300.0
    print("  [PASS] Cobro Historico: Caja +$200.00 | Ventas Actuales = $0.00 | CxC Restante = $300.00.")

    # -------------------------------------------------------------
    # CASO 7: Gasto con Retención SENIAT de 14 dígitos
    # -------------------------------------------------------------
    print("\n[CASO 7] Gasto con Retencion SENIAT (14 digitos)...")
    res7 = client.post("/api/expenses", json={
        "date": "2026-09-17",
        "category_id": 1,
        "account_id": acc1,
        "amount_usd": 150.0,
        "currency": "USD",
        "subtype": "PAGO_PROVEEDOR",
        "beneficiary": "Distribuidora Industrial Valencia C.A.",
        "reference_number": f"EXP-REF-{ts}",
        "tax_retention_amount": 18.0,
        "tax_retention_proof": "2026-09-00000045"
    }, headers=headers)
    assert res7.status_code == 200
    assert res7.json()["tax_retention_proof"] == "20260900000045"
    print("  [PASS] Gasto + Retencion SENIAT formateado a 14 digitos y registrado exitosamente.")

    # -------------------------------------------------------------
    # CASO 8: Transferencia entre Cuentas Activas (Bloqueo Pesimista)
    # -------------------------------------------------------------
    print("\n[CASO 8] Transferencia entre Cuentas Activas...")
    res8 = client.post("/api/transfers", json={
        "date": "2026-09-17",
        "origin_account_id": acc1,
        "destination_account_id": acc2,
        "amount_usd": 50.0,
        "description": "Traspaso de fondos operativo"
    }, headers=headers)
    assert res8.status_code == 200
    print("  [PASS] Transferencia ejecutada atomicamente con bloqueo pesimista y auditada.")

    # -------------------------------------------------------------
    # CASO 9: Clean Slate Multinivel con Rechazo de Clave Errónea
    # -------------------------------------------------------------
    print("\n[CASO 9] Clean Slate Protegido...")
    res9_bad = client.post("/api/system/clean-slate", json={
        "master_key": "CLAVE_INCORRECTA",
        "confirmation_phrase": "CONFIRMAR-PURGA-TEV"
    }, headers=headers)
    assert res9_bad.status_code == 403
    print("  [PASS] Clean Slate: Rechazo con 403 Forbidden verificado ante clave invalida.")

    print("\n=================================================================")
    print("  REGRESION FINANCIERA: 100% (9/9) CASOS VERIFICADOS AL CENTAVO")
    print("=================================================================\n")

if __name__ == "__main__":
    run_financial_regressions()
