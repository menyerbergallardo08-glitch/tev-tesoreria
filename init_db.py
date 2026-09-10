import os
import sys
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import engine, Base, SessionLocal
import models
from models import Branch, CashRegister, User, TreasuryAccount, BudgetCategory, SystemSetting
import auth

def run_migrations():
    with engine.begin() as conn:
        is_sqlite = engine.dialect.name == 'sqlite'
        Base.metadata.create_all(bind=conn)

        columns_to_add = [
            ('users', 'branch_id', 'INTEGER'),
            ('transactions', 'branch_id', 'INTEGER'),
            ('transactions', 'cash_register_id', 'INTEGER'),
            ('daily_cash_closes', 'branch_id', 'INTEGER'),
            ('daily_cash_closes', 'cash_register_id', 'INTEGER'),
            ('transactions', 'doc_type', 'VARCHAR(30)'),
            ('transactions', 'doc_number', 'VARCHAR(100)'),
            ('transactions', 'client_name', 'VARCHAR(150)'),
            ('transactions', 'client_rif', 'VARCHAR(50)'),
            ('transactions', 'is_credit', 'BOOLEAN'),
            ('transactions', 'credit_status', 'VARCHAR(20)'),
            ('transactions', 'credit_original_amount_usd', 'FLOAT'),
            ('transactions', 'credit_balance_pending_usd', 'FLOAT'),
            ('transactions', 'parent_transaction_id', 'INTEGER'),
            ('transactions', 'pos_terminal', 'VARCHAR(50)'),
            ('transactions', 'pos_lot_number', 'VARCHAR(50)'),
            ('transactions', 'tax_retention_amount', 'FLOAT'),
            ('transactions', 'tax_retention_proof', 'VARCHAR(100)')
        ]

        for table, col, coltype in columns_to_add:
            try:
                if is_sqlite:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype};"))
                else:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {coltype};"))
            except Exception:
                pass

def init_all():
    run_migrations()
    db = SessionLocal()
    try:
        # 1. Ensure default Branch exists
        branch = db.query(Branch).filter(Branch.code == 'TEV-CENTRO').first()
        if not branch:
            branch = Branch(
                code='TEV-CENTRO',
                name='Sede Principal - Valencia Centro',
                address='Av. Bolívar / Centro de Valencia, Carabobo',
                phone='0414-1234567',
                is_active=True
            )
            db.add(branch)
            db.commit()
            db.refresh(branch)

        # 2. Ensure default Cash Register exists
        cash_reg = db.query(CashRegister).filter(CashRegister.branch_id == branch.id, CashRegister.code == 'CAJA-01').first()
        if not cash_reg:
            cash_reg = CashRegister(
                branch_id=branch.id,
                code='CAJA-01',
                name='Caja Mostrador Principal',
                is_active=True
            )
            db.add(cash_reg)
            db.commit()

        # 3. Ensure Default Users exist
        default_users = [
            ('cajera', 'cajera123', 'Cajera Turno Mañana', 'cajera'),
            ('administradora', 'admin123', 'Lcda. María Administradora', 'administradora'),
            ('directivo', 'directivo123', 'Director General TEV', 'directivo'),
            ('consultor', 'admin123', 'Consultor Financiero', 'directivo')
        ]
        for uname, pwd, fname, role in default_users:
            u = db.query(User).filter(User.username == uname).first()
            if not u:
                u = User(
                    username=uname,
                    password_hash=auth.hash_password(pwd),
                    full_name=fname,
                    role=role,
                    branch_id=branch.id
                )
                db.add(u)
            else:
                if not u.branch_id:
                    u.branch_id = branch.id

        # 4. Ensure Default Treasury Accounts exist
        default_accounts = [
            ('Efectivo USD (Caja Tienda)', 'USD', 'EFECTIVO', 0.0),
            ('Efectivo VES (Gaveta Tienda)', 'VES', 'EFECTIVO', 0.0),
            ('Banesco Banco Universal (VES)', 'VES', 'BANCO', 0.0),
            ('Bancaribe (VES)', 'VES', 'BANCO', 0.0),
            ('Banco de Venezuela (VES)', 'VES', 'BANCO', 0.0),
            ('Banco Nacional de Crédito - BNC (VES)', 'VES', 'BANCO', 0.0),
            ('Cashea (VES)', 'VES', 'BANCO', 0.0),
            ('Banesco Panamá (USD)', 'USD', 'BANCO', 0.0),
            ('Zelle / Custodia USD', 'USD', 'BANCO', 0.0),
            ('Billetera Binance USDT', 'USDT', 'BILLETERA', 0.0)
        ]
        for name, curr, atype, init_bal in default_accounts:
            acc = db.query(TreasuryAccount).filter(TreasuryAccount.name == name).first()
            if not acc:
                acc = TreasuryAccount(
                    name=name,
                    currency=curr,
                    account_type=atype,
                    initial_balance=init_bal,
                    is_active=True
                )
                db.add(acc)

        # 5. Ensure Default Settings exist
        settings = [
            ('tasa_bcv', '36.50'),
            ('tasa_paralelo', '39.20'),
            ('alerta_saldo_minimo_usd', '500'),
            ('alerta_descuadre_caja_usd', '5')
        ]
        for k, v in settings:
            s = db.query(SystemSetting).filter(SystemSetting.key == k).first()
            if not s:
                s = SystemSetting(key=k, value=v)
                db.add(s)

        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

# Alias for backwards compatibility
init_database = init_all

if __name__ == '__main__':
    init_all()
    print("Database initialized.")
