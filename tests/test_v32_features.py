import os
import sys
import time
import json
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

        # 8. Test Live Sale with doc_type = NOTA_CREDITO and historical original_sale_date
        res_live_nc = client.post("/api/sales/live", json={
            "account_id": acc.id if acc else 1,
            "amount_original": 45.0,
            "currency": "USD",
            "doc_type": "NOTA_CREDITO",
            "doc_number": f"NC-HIST-{ts}",
            "client_name": "Cliente Devolucion Hist",
            "payment_method": "NOTA_CREDITO",
            "original_sale_date": "2026-08-15",
            "description": "Devolucion de venta previa al sistema",
            "is_credit": False
        }, headers=headers)
        assert res_live_nc.status_code == 200

        # 9. Test Live Sale of Contado Paid with prior NOTA_CREDITO ($0 cash drawer impact)
        res_live_paid_nc = client.post("/api/sales/live", json={
            "account_id": acc.id if acc else 1,
            "amount_original": 120.0,
            "currency": "USD",
            "doc_type": "NOTA_ENTREGA",
            "doc_number": f"NE-PAGADA-NC-{ts}",
            "client_name": "Cliente Usando Saldo a Favor",
            "payment_method": "NOTA_CREDITO",
            "reference_number": f"NC-PREVIA-{ts}",
            "original_sale_date": "2026-07-10",
            "description": "Pagado con NC previa",
            "is_credit": False
        }, headers=headers)
        assert res_live_paid_nc.status_code == 200

        # 10. Test 100% Credit Sale without downpayment (Zero impact on liquid drawer / Binance)
        res_credit_zero = client.post("/api/sales/live", json={
            "amount_original": 250.0,
            "currency": "USD",
            "doc_type": "NOTA_ENTREGA",
            "doc_number": f"NE-CRED-ZERO-{ts}",
            "client_name": "Cliente Credito Puro",
            "seller_code": "25",
            "is_credit": True,
            "initial_downpayment_amount": 0.0
        }, headers=headers)
        assert res_credit_zero.status_code == 200
        cred_tx_id = res_credit_zero.json()["id"]
        cred_tx = db.query(Transaction).filter(Transaction.id == cred_tx_id).first()
        assert cred_tx.amount_usd == 0.0
        assert cred_tx.amount_original == 0.0
        assert cred_tx.credit_balance_pending_usd == 250.0
        assert cred_tx.seller_code == "25"
        assert cred_tx.seller_name == "Daniel Zabala"
        # Ensure account is Cartera CxC
        cxc_acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == cred_tx.account_id).first()
        assert cxc_acc.account_type == 'CXC' or 'CxC' in cxc_acc.name

        # 11. Test CxC Payment inherits seller
        res_cxc_pay = client.post("/api/cxc/payments", json={
            "transaction_id": cred_tx_id,
            "amount_usd": 100.0,
            "account_id": acc.id if acc else 1,
            "payment_type": "COBRO",
            "description": "Cobro parcial de credito puro"
        }, headers=headers)
        assert res_cxc_pay.status_code == 200
        abono_id = res_cxc_pay.json()["id"]
        abono_tx = db.query(Transaction).filter(Transaction.id == abono_id).first()
        assert abono_tx.seller_code == "25"
        assert abono_tx.seller_name == "Daniel Zabala"
        assert abono_tx.amount_usd == 100.0

        # 12. Test Commission Calculations (Cash-basis + Coordination 1%)
        # Register a cash sale by Orianna (23) and office (01)
        res_orianna = client.post("/api/sales/live", json={
            "account_id": acc.id if acc else 1,
            "amount_original": 500.0,
            "currency": "USD",
            "doc_type": "NOTA_ENTREGA",
            "doc_number": f"NE-ORIANNA-{ts}",
            "client_name": "Cliente Directo Orianna",
            "seller_code": "23",
            "is_credit": False
        }, headers=headers)
        assert res_orianna.status_code == 200

        res_office = client.post("/api/sales/live", json={
            "account_id": acc.id if acc else 1,
            "amount_original": 300.0,
            "currency": "USD",
            "doc_type": "FACTURA_FISCAL",
            "doc_number": f"FAC-OFICINA-{ts}",
            "client_name": "Cliente Mostrador Oficina",
            "seller_code": "01",
            "is_credit": False
        }, headers=headers)
        assert res_office.status_code == 200

        # Query /api/commissions
        res_comm = client.get("/api/commissions", headers=headers)
        assert res_comm.status_code == 200
        comm_data = res_comm.json()
        assert "sellers" in comm_data
        assert "totals" in comm_data
        assert "coordination_detail" in comm_data

        sellers_by_code = {s["code"]: s for s in comm_data["sellers"]}
        # Daniel Zabala (25): 5% on collected
        assert "25" in sellers_by_code
        assert sellers_by_code["25"]["rate_pct"] == "5%"
        assert sellers_by_code["25"]["cxc_cobradas_usd"] >= 100.0
        assert sellers_by_code["25"]["comision_directa_usd"] > 0.0

        # Orianna Montilla (23): 1% direct + 1% coordination on team
        assert "23" in sellers_by_code
        assert sellers_by_code["23"]["rate_pct"] == "1%"
        assert sellers_by_code["23"]["comision_coordinacion_usd"] > 0.0
        assert sellers_by_code["23"]["comision_total_usd"] == round(sellers_by_code["23"]["comision_directa_usd"] + sellers_by_code["23"]["comision_coordinacion_usd"], 2)

        # Oficina (01): 0%
        assert "01" in sellers_by_code
        assert sellers_by_code["01"]["comision_total_usd"] == 0.0

        # Bimoneda y Ranking de Ventas
        assert "sales_ranking" in comm_data
        assert "total_comisiones_a_pagar_bs" in comm_data["totals"]
        assert "total_comisiones_a_pagar_usd" in comm_data["totals"]
        assert "total_ventas_comerciales_usd" in comm_data["totals"]
        assert comm_data["coordination_detail"]["title"] == "Coordinador de Ventas"

        # 13. Test Cash Close Summary Separation: Venta Real vs Total Cobrado
        res_summary = client.get("/api/cash-close/summary", headers=headers)
        assert res_summary.status_code == 200
        summary_data = res_summary.json()
        assert "sales_summary" in summary_data
        assert "collections_summary" in summary_data
        assert "venta_real_del_dia_usd" in summary_data["sales_summary"]
        assert "total_cobrado_dia_usd" in summary_data["collections_summary"]
        assert "ventas_contado_usd" in summary_data["sales_summary"]
        assert "ventas_credito_usd" in summary_data["sales_summary"]
        # Venta real del día must equal contado + credito - devoluciones
        ss = summary_data["sales_summary"]
        assert ss["venta_real_del_dia_usd"] == round(ss["ventas_contado_usd"] + ss["ventas_credito_usd"] - ss["devoluciones_usd"], 2)

        # 14. Test Manuals Endpoints
        res_man_cajera = client.get("/api/manuals/cajera", headers=headers)
        assert res_man_cajera.status_code == 200
        man_data = res_man_cajera.json()
        assert man_data["role"] == "cajera"
        assert "Manual Operativo" in man_data["title"]
        assert len(man_data["content"]) > 100

        res_man_admin = client.get("/api/manuals/administradora", headers=headers)
        assert res_man_admin.status_code == 200
        assert "content" in res_man_admin.json()

        res_man_dl = client.get("/api/manuals/cajera/download", headers=headers)
        assert res_man_dl.status_code == 200

        res_man_404 = client.get("/api/manuals/desconocido", headers=headers)
        assert res_man_404.status_code == 404

        # 15. Test Cajera Role Allowed to Update Supplier
        cajera_user = db.query(User).filter(User.role == 'cajera').first()
        if not cajera_user:
            cajera_user = User(username=f"cajera_test_{ts}", role="cajera", full_name="Cajera Test", password_hash="xxx", is_active=True)
            db.add(cajera_user)
            db.commit()
            db.refresh(cajera_user)
        cajera_token = create_access_token({"sub": cajera_user.username, "role": cajera_user.role})
        cajera_headers = {"Authorization": f"Bearer {cajera_token}"}

        # Cajera creates or updates supplier
        res_sup_cajera = client.put(f"/api/suppliers/{sup_id}", json={
            "phone": "0414-7777777",
            "bank_details": "Pago Movil Mercantil 0414..."
        }, headers=cajera_headers)
        assert res_sup_cajera.status_code == 200
        assert res_sup_cajera.json()["phone"] == "0414-7777777"

        # 16. Test Emergency Expense Editing with Mandatory Reason & Audit
        test_acc = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).first()
        from schemas.transactions import TransactionCreate
        import datetime
        create_egreso_res = client.post("/api/transactions", json={
            "date": str(datetime.date.today()),
            "movement_type": "EGRESO",
            "subtype": "GASTO_OPERATIVO",
            "account_id": test_acc.id,
            "category_id": 1,
            "amount_original": 100.0,
            "currency": "USD",
            "exchange_rate": 1.0,
            "beneficiary": "Proveedor Servicio Electrico",
            "reference_number": f"TEST-EMERG-{ts}",
            "description": "Gasto operativo inicial"
        }, headers=cajera_headers)
        assert create_egreso_res.status_code == 200
        egreso_id = create_egreso_res.json()["id"]

        # Intentar modificar monto sin justificación debe fallar (400)
        res_fail = client.patch(f"/api/transactions/{egreso_id}", json={
            "amount_original": 150.0
        }, headers=cajera_headers)
        assert res_fail.status_code == 400
        assert "motivo" in res_fail.json()["detail"].lower()

        # Modificar monto CON justificación obligatoria debe ser exitoso (200)
        res_success = client.patch(f"/api/transactions/{egreso_id}", json={
            "amount_original": 150.0,
            "edit_reason": "Error de digitación en punto de venta, monto real era 150"
        }, headers=cajera_headers)
        assert res_success.status_code == 200
        assert res_success.json()["transaction"]["amount_original"] == 150.0
        assert res_success.json()["transaction"]["amount_usd"] == 150.0

        # Verificar que el AuditLog tenga la acción CORRECCION_EMERGENCIA_EGRESO
        from models import AuditLog
        audit_entry = db.query(AuditLog).filter(
            AuditLog.entity_id == str(egreso_id),
            AuditLog.action == "CORRECCION_EMERGENCIA_EGRESO"
        ).order_by(AuditLog.id.desc()).first()
        assert audit_entry is not None
        det_dict = json.loads(audit_entry.details_json) if isinstance(audit_entry.details_json, str) else (audit_entry.details_json or {})
        assert "Error de digitación" in det_dict.get("reason", "")

        # 17. Test Director KPIs reflects Operational Corrections
        res_kpi = client.get("/api/dashboard/director-kpis", headers=headers)
        assert res_kpi.status_code == 200
        kpi_json = res_kpi.json()
        assert "operational_corrections_kpi" in kpi_json
        assert kpi_json["operational_corrections_kpi"]["total_count"] >= 1
        found_in_recent = any(c["entity_id"] == str(egreso_id) for c in kpi_json["operational_corrections_kpi"]["recent_corrections"])
        assert found_in_recent is True

        # 18. Test Custom Exchange Rate for VES Payment (PHEBO ELECTRIC case: Bs. 574.156,50 @ 1005 -> $571.30)
        res_rate_test = client.post("/api/transactions", json={
            "date": "2026-10-22",
            "movement_type": "EGRESO",
            "subtype": "PAGO_PROVEEDOR",
            "account_id": test_acc.id,
            "amount_original": 574156.50,
            "currency": "VES",
            "exchange_rate": 1005.0,
            "beneficiary": "PHEBO ELECTRIC, C.A",
            "reference_number": f"PHEBO-{ts}",
            "description": "Pago proveedor a tasa 1005"
        }, headers=cajera_headers)
        assert res_rate_test.status_code == 200
        rate_tx = res_rate_test.json()
        assert rate_tx["exchange_rate"] == 1005.0
        assert rate_tx["amount_usd"] == 571.30

        # 19. Test Custom Exchange Rate with Explicit USD Base (LITTMAN case: Bs. 321.850 @ 1025, base $314)
        res_littman_test = client.post("/api/transactions", json={
            "date": "2026-10-22",
            "movement_type": "EGRESO",
            "subtype": "PAGO_PROVEEDOR",
            "account_id": test_acc.id,
            "amount_original": 321850.00,
            "currency": "VES",
            "exchange_rate": 1025.0,
            "amount_usd": 314.00,
            "beneficiary": "LITTMAN INVERSIONES C.A.",
            "reference_number": f"LITTMAN-{ts}",
            "description": "Pago NE 612686 [Descuento Pronto Pago: -5% (-$16.50) | Factura: $330.50 | Neto Pagado: 321850]"
        }, headers=cajera_headers)
        assert res_littman_test.status_code == 200
        littman_tx = res_littman_test.json()
        assert littman_tx["exchange_rate"] == 1025.0
        # 20. Test SENIAT Client Retention Abono (Mango Bajito scenario)
        mango_sale = client.post("/api/sales", json={
            "doc_type": "NOTA_ENTREGA",
            "doc_number": f"NE-MANGO-{ts}",
            "client_name": "MANGO BAJITO VALENCIA C.A.",
            "client_rif": "J-31445566-7",
            "payment_method": "TRANSFERENCIA",
            "is_credit": True,
            "amount_usd": 100.0,
            "currency": "USD"
        }, headers=cajera_headers)
        assert mango_sale.status_code == 200
        mango_data = mango_sale.json()
        mango_credit_id = mango_data["id"]

        # Abono vía Retención SENIAT
        res_ret = client.post(f"/api/receivables/{mango_credit_id}/abono", json={
            "amount_original": 75.0,
            "currency": "USD",
            "is_retention": True,
            "tax_retention_proof": "20261000000045",
            "date": "2026-10-30",
            "description": "Retención SENIAT IVA 75% aplicada por Mango Bajito"
        }, headers=cajera_headers)
        assert res_ret.status_code == 200
        ret_json = res_ret.json()
        assert ret_json["success"] is True
        assert ret_json["is_retention"] is True

        # Verificar que el saldo pendiente se rebajó a $25
        db.expire_all()
        parent_tx = db.query(Transaction).filter(Transaction.id == mango_credit_id).first()
        assert parent_tx.credit_balance_pending_usd == 25.0
        assert parent_tx.credit_status == "PARCIALMENTE_PAGADO"

        # Verificar que la transacción de retención tiene cuenta RETENCION_CLIENTE
        abono_tx = db.query(Transaction).filter(
            Transaction.parent_transaction_id == mango_credit_id,
            Transaction.subtype == "RETENCION_CLIENTE_CXC"
        ).first()
        assert abono_tx is not None
        assert abono_tx.doc_type == "RETENCION_SENIAT"
        assert abono_tx.tax_retention_proof == "20261000000045"
        assert abono_tx.tax_retention_amount == 75.0
        ret_account = db.query(TreasuryAccount).filter(TreasuryAccount.id == abono_tx.account_id).first()
        assert ret_account.account_type == "RETENCION_CLIENTE"

        # 21. Test Emergency Edit with Pronto Pago Adjustment
        patch_res = client.patch(f"/api/transactions/{littman_tx['id']}", json={
            "amount_original": 297.45,
            "currency": "USD",
            "description": "Pago NE 612686 [Descuento Pronto Pago: -10% (Monto: 33.05) | Factura: 330.50 | Neto Pagado: 297.45]",
            "edit_reason": "Ajuste de pronto pago de 5% a 10% acordado con proveedor"
        }, headers=headers)
        assert patch_res.status_code == 200
        updated_tx = db.query(Transaction).filter(Transaction.id == littman_tx["id"]).first()
        assert updated_tx.amount_original == 297.45
        assert updated_tx.amount_usd == 297.45
        assert "Descuento Pronto Pago: -10%" in updated_tx.description

        # 22. Test BCV 4:00 PM Policy
        from core.bcv import resolve_effective_bcv_rate
        import datetime
        # Simular Miércoles 16:30 (4:30 PM)
        wed_evening = datetime.datetime(2026, 10, 28, 16, 30, 0)
        res_evening = resolve_effective_bcv_rate(
            db,
            now_dt=wed_evening,
            mock_fresh_rate=950.0
        )
        assert "Jornada en curso" in res_evening["policy_applied"]
        assert res_evening["next_rate_tomorrow"] == 950.0

        # Simular Miércoles 11:00 AM (horario laboral matutino)
        wed_morning = datetime.datetime(2026, 10, 28, 11, 0, 0)
        res_morning = resolve_effective_bcv_rate(
            db,
            now_dt=wed_morning,
            mock_fresh_rate=920.0
        )
        assert res_morning["rate"] == 920.0

    finally:
        db.close()


