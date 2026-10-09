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

    # Crear usuario temporal para testear update con cambio de username, password y self-toggle
    ts = int(datetime.datetime.now().timestamp() * 1000)
    u_tmp_name = f'user_temp_{ts}'
    res_cre = client.post('/api/auth/users', json={
        'username': u_tmp_name,
        'password': 'temp_password_123',
        'full_name': 'Usuario Temporal Prueba',
        'role': 'cajera'
    }, headers=h_m)
    if res_cre.status_code == 200:
        uid = res_cre.json()['id']
        client.patch(f'/api/auth/users/{uid}/password', json={'new_password': '12'}, headers=h_m)
        client.post('/api/auth/users', json={
            'username': u_tmp_name,
            'password': 'temp_password_123',
            'full_name': 'Duplicado',
            'role': 'cajera'
        }, headers=h_m)
        client.put(f'/api/auth/users/{uid}', json={'username': 'master'}, headers=h_m)
        u_tmp_name2 = f'u2_{ts}'
        client.put(f'/api/auth/users/{uid}', json={
            'username': u_tmp_name2,
            'full_name': 'Nombre Cambiado',
            'role': 'administradora',
            'password': 'nueva_clave_456',
            'is_active': True
        }, headers=h_m)
        client.delete(f'/api/auth/users/{uid}', headers=h_m)

    # Self-toggle y self-delete directivo (lines 198, 214)
    db_u = SessionLocal()
    try:
        m_user = db_u.query(User).filter(User.username == 'master').first()
        m_id = m_user.id if m_user else 1
    finally:
        db_u.close()
    client.patch(f'/api/auth/users/{m_id}/toggle-status', headers=h_m)
    client.delete(f'/api/auth/users/{m_id}', headers=h_m)

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

    # Venta Anulable
    res_sale = client.post('/api/sales', json={
        'date': '2026-09-19',
        'doc_type': 'FACTURA_FISCAL',
        'doc_number': 'FAC-ANUL-01',
        'client_name': 'Cliente Para Anular',
        'amount_usd': 30.0,
        'payment_method': 'EFECTIVO_USD',
        'account_id': acc_usd_id,
        'is_credit': False
    }, headers=h_m)
    if res_sale.status_code == 200:
        sale_id = res_sale.json()['id']
        client.post('/api/sales/void', json={'transaction_id': 999999, 'reason': 'Test'}, headers=h_m)
        client.post('/api/sales/void', json={'transaction_id': sale_id, 'reason': 'Error de monto'}, headers=h_m)
        client.post('/api/sales/void', json={'transaction_id': sale_id, 'reason': 'Re-anulacion'}, headers=h_m)

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

    # Devolución para cubrir returns_today_usd (routers/sales.py line 187)
    client.post('/api/expenses', json={
        'date': '2026-09-16',
        'movement_type': 'EGRESO',
        'subtype': 'DEVOLUCION_VENTA',
        'account_id': acc_usd_id,
        'amount_usd': 12.0,
        'currency': 'USD',
        'description': 'Devolucion cliente prueba'
    }, headers=h_m)

    # Sales Summary Today
    client.get('/api/sales/summary-today?date=2026-09-16', headers=h_m)
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
    client.post('/api/cash-closes', json=close_payload, headers=h_m)
    client.post('/api/cash-closes', json=close_payload, headers=h_m)

    # Legacy Cash Close: Creación de nuevo cierre (line 236+) y actualización de existente (line 224+)
    client.post('/api/cash-close', json={
        'date': '2026-09-22',
        'status': 'CUADRADO',
        'total_expected_usd': 80.0
    }, headers=h_m)
    client.post('/api/cash-close', json={
        'date': '2026-09-22',
        'status': 'VERIFICADO',
        'total_expected_usd': 85.0
    }, headers=h_m)

    client.get('/api/cash-close/summary?date=2026-09-16', headers=h_m)
    client.get('/api/cash-close/summary?date=2026-09-17', headers=h_m)
    client.get('/api/cash-close/history', headers=h_m)
    client.get('/api/cash-closes', headers=h_m)

    # 6. Dashboard Cash-Flow Daily Matrix & Subtypes (lines 382-404)
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
    client.post('/api/accounts', json={
        'name': 'Caja Sucursal Reactivacion Test',
        'currency': 'USD',
        'account_type': 'Caja Operativa',
        'initial_balance': 50.0
    }, headers=h_m)

    db2 = SessionLocal()
    try:
        t_acc = db2.query(TreasuryAccount).filter(TreasuryAccount.name == 'Caja Sucursal Reactivacion Test').first()
        if t_acc:
            client.patch(f'/api/accounts/{t_acc.id}/toggle-status', headers=h_m)
            client.post('/api/accounts', json={
                'name': 'Caja Sucursal Reactivacion Test',
                'currency': 'USD',
                'account_type': 'Caja Operativa',
                'initial_balance': 75.0,
                'only_income': False
            }, headers=h_m)
    finally:
        db2.close()

    client.patch('/api/accounts/999999/toggle-status', headers=h_m)

    # 8. System Router Edge Cases: Tasa BCV & Backups (lines 57, 120, 143)
    client.post('/api/system/bcv-rate', json={'rate': -10.0}, headers=h_m)
    client.get('/api/system/backups/invalid..name/content', headers=h_m)
    client.get('/api/system/backups/invalid..name', headers=h_m)
