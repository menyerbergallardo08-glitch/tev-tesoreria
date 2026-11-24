import os
import sys
import json
import datetime
from fastapi.testclient import TestClient

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from main import app
from database import SessionLocal
from models import User, Transaction, TreasuryAccount, AuditLog
from core.security import create_access_token

client = TestClient(app)


def test_edit_transaction_date_with_audit_trail():
    db = SessionLocal()
    created_tx_id = None
    audit_ids_to_clean = []
    try:
        # Prefer a cajera user to verify that all roles can edit date with audit trail
        user = db.query(User).filter(User.role == "cajera").first() or db.query(User).first()
        assert user is not None, "Debe existir al menos un usuario en BD"
        account = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).first()
        assert account is not None, "Debe existir al menos una cuenta activa en BD"

        token = create_access_token({"sub": user.username, "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}

        # Create a test supplier payment transaction
        tx = Transaction(
            date=datetime.date(2026, 11, 23),
            invoice_date=datetime.date(2026, 11, 20),
            movement_type="EGRESO",
            subtype="PAGO_PROVEEDOR",
            account_id=account.id,
            amount_original=1269.04,
            currency="USDT",
            exchange_rate=1.0,
            amount_usd=1269.04,
            reference_number="TEST_DATE_EDIT_001",
            doc_number="208511",
            beneficiary="J-00000828-0 - ALCAVE, C.A.",
            description="PAGO FACT 208511 TEST",
            status="REGISTRADO",
            created_by_id=user.id,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        created_tx_id = tx.id

        # 1. Verify GET /api/transactions returns date, invoice_date, and doc_number
        res_list = client.get("/api/transactions", params={"date": "2026-11-23", "limit": 50}, headers=headers)
        assert res_list.status_code == 200
        found = next((i for i in res_list.json()["items"] if i["id"] == created_tx_id), None)
        assert found is not None
        assert found["date"] == "2026-11-23"
        assert found["invoice_date"] == "2026-11-20"
        assert found["doc_number"] == "208511"

        # 2. Attempting to change date WITHOUT edit_reason must be rejected (400)
        res_fail = client.patch(
            f"/api/transactions/{created_tx_id}",
            json={"date": "2026-11-22"},
            headers=headers,
        )
        assert res_fail.status_code == 400

        # 3. Changing date and invoice_date WITH edit_reason must succeed (200) and leave audit trace
        res_ok = client.patch(
            f"/api/transactions/{created_tx_id}",
            json={
                "date": "2026-11-21",
                "invoice_date": "2026-11-19",
                "edit_reason": "Error de digitación en fecha de factura proveedor",
            },
            headers=headers,
        )
        assert res_ok.status_code == 200, res_ok.text
        body = res_ok.json()
        assert body["success"] is True
        assert body["transaction"]["date"] == "2026-11-21"
        assert body["transaction"]["invoice_date"] == "2026-11-19"

        # 4. Verify DB persistence
        db.expire_all()
        updated_tx = db.query(Transaction).filter(Transaction.id == created_tx_id).first()
        assert updated_tx.date == datetime.date(2026, 11, 21)
        assert updated_tx.invoice_date == datetime.date(2026, 11, 19)

        # 5. Verify AuditLog trace ("huella y traza")
        audit = (
            db.query(AuditLog)
            .filter(AuditLog.entity_type == "Transaction", AuditLog.entity_id == str(created_tx_id))
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit is not None, "No se registró la huella en AuditLog"
        audit_ids_to_clean.append(audit.id)
        details = json.loads(audit.details_json)
        assert details["previous"]["date"] == "2026-11-23"
        assert details["changes"]["date"] == "2026-11-21"
        assert details["diff"]["date"] == {"from": "2026-11-23", "to": "2026-11-21"}
        assert details["diff"]["invoice_date"] == {"from": "2026-11-20", "to": "2026-11-19"}
        assert details["reason"] == "Error de digitación en fecha de factura proveedor"
        assert details["updated_by"] == user.username
        assert details["role"] == user.role
    finally:
        if audit_ids_to_clean:
            db.query(AuditLog).filter(AuditLog.id.in_(audit_ids_to_clean)).delete(synchronize_session=False)
        if created_tx_id is not None:
            db.query(Transaction).filter(Transaction.id == created_tx_id).delete(synchronize_session=False)
        db.commit()
        db.close()
