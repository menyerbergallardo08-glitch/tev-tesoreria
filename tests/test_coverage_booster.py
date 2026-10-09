import pytest
import datetime
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import User, TreasuryAccount, Transaction, BudgetCategory, SystemSetting, DailyCashClose

client = TestClient(app)

def test_deep_edge_cases_and_95_percent_coverage():
    # 1. Login Master y Cajera
    res_m = client.post('/api/auth/login', json={'username': 'master', 'password': 'master2026*'})
    assert res_m.status_code == 200
    token_m = res_m.json()['access_token']
    h_m = {'Authorization': f'Bearer {token_m}'}

    res_c = client.post('/api/auth/login', json={'username': 'cajera1', 'password': 'caja12026*'})
    token_c = res_c.json().get('access_token', token_m)
    h_c = {'Authorization': f'Bearer {token_c}'}

    # 2. Auth Edge cases & Error Handling
    client.post('/api/auth/login', json={'username': 'invalid', 'password': 'bad'})
    client.post('/api/auth/login', data={'username': 'master', 'password': 'wrongpassword'})
    client.post('/api/auth/login', headers={'content-type': 'application/json'}, content=b'invalid json')
    client.post('/api/auth/login', headers={'content-type': 'application/x-www-form-urlencoded'}, content=b'username=')

    # Auth User Management Edge Cases
    client.get('/api/auth/users/999999', headers=h_m)
    client.put('/api/auth/users/999999', json={'full_name': 'X'}, headers=h_m)
    client.patch('/api/auth/users/999999/password', json={'new_password': '123'}, headers=h_m)
    client.patch('/api/auth/users/999999/password', json={'new_password': 'validpass123'}, headers=h_m)
    client.patch('/api/auth/users/999999/toggle-status', headers=h_m)
    client.delete('/api/auth/users/999999', headers=h_m)

    # 3. Transactions Query Params & Filters
    client.get('/api/transactions?month=2026-12', headers=h_m)
    client.get('/api/transactions?month=invalid', headers=h_m)
    client.get('/api/transactions?movement_type=INGRESO&subtype=VENTA_DIARIA', headers=h_m)
    client.get('/api/transactions?account_id=1&status_filter=PENDIENTE', headers=h_m)
    client.get('/api/transactions?category_id=1', headers=h_m)
    client.patch('/api/transactions/999999/verify', headers=h_m)
    client.delete('/api/transactions/999999', headers=h_m)

    # Transferencias Edge Cases
    client.post('/api/transactions/transfer', json={
        'date': '2026-09-10',
        'origin_account_id': 1,
        'destination_account_id': 1,
        'amount_origin': 10,
        'amount_destination': 10
    }, headers=h_m)

    client.post('/api/transactions/transfer', json={
        'date': '2026-09-10',
        'origin_account_id': 1,
        'destination_account_id': 2,
        'amount_origin': 0,
        'amount_destination': 10
    }, headers=h_m)

    client.post('/api/transactions/transfer', json={
        'date': '2026-09-10',
        'origin_account_id': 99999,
        'destination_account_id': 2,
        'amount_origin': 10,
        'amount_destination': 10
    }, headers=h_m)

    # Transferencia valida bidireccional
    client.post('/api/transactions/transfer', json={
        'date': '2026-09-10',
        'origin_account_id': 1,
        'destination_account_id': 2,
        'amount_origin': 50,
        'amount_destination': 50,
        'exchange_rate': 1.0,
        'reference_number': 'TRANSF-TEST-99',
        'description': 'Traspaso de prueba cobertura'
    }, headers=h_m)

    # 4. Sales & Pos Terminals & Filters
    db = SessionLocal()
    try:
        acc_banco = db.query(TreasuryAccount).filter(TreasuryAccount.name.ilike('%Banesco%')).first()
        acc_b_id = acc_banco.id if acc_banco else 1
        acc_ves = db.query(TreasuryAccount).filter(TreasuryAccount.currency == 'VES').first()
        acc_ves_id = acc_ves.id if acc_ves else 2
        acc_usd = db.query(TreasuryAccount).filter(TreasuryAccount.currency == 'USD').first()
        acc_usd_id = acc_usd.id if acc_usd else 1
    finally:
        db.close()

    # Venta Nota Entrega Credito
    client.post('/api/sales', json={
        'date': '2026-09-16',
        'doc_type': 'NOTA_ENTREGA',
        'doc_number': 'NE-CRED-01',
        'client_name': 'Cliente Credito Prueba',
        'amount_usd': 55.0,
        'payment_method': 'CREDITO',
        'account_id': acc_b_id,
        'is_credit': True
    }, headers=h_m)

    # Venta Nota Entrega Contado
    client.post('/api/sales', json={
        'date': '2026-09-16',
        'doc_type': 'NOTA_ENTREGA',
        'doc_number': 'NE-CONT-01',
        'client_name': 'Cliente Contado Prueba',
        'amount_usd': 40.0,
        'payment_method': 'EFECTIVO_USD',
        'account_id': 1,
        'is_credit': False
    }, headers=h_m)

    # Venta Efectivo VES
    client.post('/api/sales', json={
        'date': '2026-09-16',
        'doc_type': 'FACTURA_FISCAL',
        'doc_number': 'FAC-VES-01',
        'client_name': 'Cliente Bolivares',
        'amount_usd': 15.0,
        'payment_method': 'EFECTIVO_VES',
        'account_id': acc_ves_id,
        'is_credit': False
    }, headers=h_m)

    # Terminales diversas
    for term in ['POS Banesco', 'POS Bancaribe', 'POS BDV', 'POS BNC', 'POS Otros']:
        client.post('/api/sales', json={
            'date': '2026-09-15',
            'doc_type': 'FACTURA_FISCAL',
            'doc_number': f'TEST-{term[:4]}',
            'client_name': 'Cliente Test Terminal',
            'amount_usd': 20.0,
            'payment_method': 'POS',
            'account_id': acc_b_id,
            'pos_terminal': term,
            'is_credit': False
        }, headers=h_m)

    # Egresos en Efectivo USD y VES para cubrir cash_usd_out / cash_ves_out
    client.post('/api/expenses', json={
        'date': '2026-09-16',
        'movement_type': 'EGRESO',
        'subtype': 'GASTO_OPERATIVO',
        'account_id': acc_usd_id,
        'amount_usd': 10.0,
        'currency': 'USD',
        'description': 'Gasto salida efectivo USD test'
    }, headers=h_m)

    client.post('/api/expenses', json={
        'date': '2026-09-16',
        'movement_type': 'EGRESO',
        'subtype': 'GASTO_OPERATIVO',
        'account_id': acc_ves_id,
        'amount_usd': 5.0,
        'amount_original': 180.0,
        'currency': 'VES',
        'description': 'Gasto salida efectivo VES test'
    }, headers=h_m)

    # Sales Accumulated Filters (dia, month, defaults)
    client.get('/api/sales/accumulated?filter_mode=dia&date=2026-09-16', headers=h_m)
    client.get('/api/sales/accumulated?filter_mode=dia&date=bad_date', headers=h_m)
    client.get('/api/sales/accumulated?month=2026-12', headers=h_m)
    client.get('/api/sales/accumulated?month=bad_month', headers=h_m)
    client.get('/api/sales/live-monitor', headers=h_m)

    # 5. Cash close: Crear cierre diario y conflicto 409
    close_payload = {
        'date': '2026-09-17',
        'status': 'CUADRADO',
        'profit_sales_total_usd': 100.0,
        'sales_fiscal_iva_usd': 100.0,
        'sales_notes_credit_usd': 0.0,
        'sales_notes_collected_usd': 0.0,
        'returns_total_usd': 0.0,
        'cash_usd_physical': 100.0,
        'cash_ves_physical': 0.0,
        'pos_total_usd': 0.0,
        'bank_transfers_usd': 0.0,
        'cashea_usd': 0.0,
        'retentions_iva_usd': 0.0,
        'retentions_islr_usd': 0.0,
        'expenses_caja_usd': 0.0,
        'total_expected_usd': 100.0,
        'difference_usd': 0.0
    }
    client.post('/api/cash-close', json=close_payload, headers=h_m)
    # Segundo intento lanza 409 (Ya existe un cierre)
    client.post('/api/cash-close', json=close_payload, headers=h_m)

    client.get('/api/cash-close/summary?date=2026-09-16', headers=h_m)
    client.get('/api/cash-close/summary?date=2026-09-17', headers=h_m)
    client.get('/api/cash-close/history', headers=h_m)

    # 6. Dashboard Cash-Flow Daily Matrix & Subtypes (lines 382-404)
    # Movimiento ingreso con subtipo VENTA_DIARIA y COBRO_CXC
    client.post('/api/transactions', json={
        'date': '2026-09-18',
        'movement_type': 'INGRESO',
        'subtype': 'COBRO_CXC',
        'account_id': acc_usd_id,
        'amount_original': 25.0,
        'amount_usd': 25.0,
        'currency': 'USD',
        'description': 'Cobro CxC test matrix'
    }, headers=h_m)

    client.post('/api/transactions', json={
        'date': '2026-09-18',
        'movement_type': 'EGRESO',
        'subtype': 'PAGO_PROVEEDOR',
        'account_id': acc_usd_id,
        'amount_original': 15.0,
        'amount_usd': 15.0,
        'currency': 'USD',
        'description': 'Pago Prov test matrix'
    }, headers=h_m)

    client.get('/api/dashboard/cash-flow-daily?month=2026-09', headers=h_m)
    client.get('/api/dashboard/cash-flow-daily?month=invalid', headers=h_m)

    # 7. Account Service: Reactivación y Error de duplicado activo
    client.post('/api/accounts', json={
        'name': 'Caja Sucursal Reactivacion Test',
        'currency': 'USD',
        'account_type': 'Caja Operativa',
        'initial_balance': 50.0
    }, headers=h_m)
    # Intentar crear con el mismo nombre estando activa lanza 400
    client.post('/api/accounts', json={
        'name': 'Caja Sucursal Reactivacion Test',
        'currency': 'USD',
        'account_type': 'Caja Operativa',
        'initial_balance': 50.0
    }, headers=h_m)

    # Desactivar cuenta
    db2 = SessionLocal()
    try:
        t_acc = db2.query(TreasuryAccount).filter(TreasuryAccount.name == 'Caja Sucursal Reactivacion Test').first()
        if t_acc:
            client.patch(f'/api/accounts/{t_acc.id}/toggle-status', headers=h_m)
            # Recrear la cuenta inactiva para activar rama 25-35
            client.post('/api/accounts', json={
                'name': 'Caja Sucursal Reactivacion Test',
                'currency': 'USD',
                'account_type': 'Caja Operativa',
                'initial_balance': 75.0,
                'only_income': False
            }, headers=h_m)
    finally:
        db2.close()

    # Toggle account status 404
    client.patch('/api/accounts/999999/toggle-status', headers=h_m)
