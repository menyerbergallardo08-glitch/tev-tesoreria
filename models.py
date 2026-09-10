import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class Branch(Base):
    __tablename__ = 'branches'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False) # 'TEV-CENTRO', 'TEV-NAGUANAGUA'
    name = Column(String(100), nullable=False) # 'Sede Principal - Valencia Centro'
    address = Column(String(255), default='')
    phone = Column(String(50), default='')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    cash_registers = relationship('CashRegister', back_populates='branch')
    transactions = relationship('Transaction', back_populates='branch')
    cash_closes = relationship('DailyCashClose', back_populates='branch')


class CashRegister(Base):
    __tablename__ = 'cash_registers'

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey('branches.id'), nullable=False)
    code = Column(String(20), nullable=False) # 'CAJA-01', 'CAJA-02'
    name = Column(String(100), nullable=False) # 'Caja Mostrador 1'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    branch = relationship('Branch', back_populates='cash_registers')
    transactions = relationship('Transaction', back_populates='cash_register')
    cash_closes = relationship('DailyCashClose', back_populates='cash_register')

    __table_args__ = (
        UniqueConstraint('branch_id', 'code', name='uix_branch_cash_register_code'),
    )


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(50), nullable=False, default='sistema')
    action = Column(String(50), nullable=False, index=True) # 'CREATE_SALE', 'ABONO_CXC', 'DAILY_CLOSE', 'VOID_SALE', 'UPDATE_RATE'
    entity_type = Column(String(50), nullable=False, index=True) # 'Transaction', 'DailyCashClose', 'SystemSetting'
    entity_id = Column(String(50), nullable=True)
    details_json = Column(Text, default='{}')
    ip_address = Column(String(50), default='')

    user = relationship('User', back_populates='audit_logs')


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default='cajera')  # 'cajera', 'administradora', 'directivo'
    branch_id = Column(Integer, ForeignKey('branches.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    transactions_created = relationship('Transaction', foreign_keys='Transaction.created_by_id', back_populates='creator')
    transactions_verified = relationship('Transaction', foreign_keys='Transaction.verified_by_id', back_populates='verifier')
    audit_logs = relationship('AuditLog', back_populates='user')


class BudgetCategory(Base):
    __tablename__ = 'budget_categories'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    monthly_budget_usd = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    transactions = relationship('Transaction', back_populates='category')


class TreasuryAccount(Base):
    __tablename__ = 'treasury_accounts'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    currency = Column(String(10), nullable=False)  # 'USD', 'VES', 'USDT'
    account_type = Column(String(20), nullable=False)  # 'EFECTIVO', 'BANCO', 'BILLETERA'
    initial_balance = Column(Float, default=0.0)
    only_income = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    transactions_origin = relationship('Transaction', foreign_keys='Transaction.account_id', back_populates='account')
    transactions_destination = relationship('Transaction', foreign_keys='Transaction.destination_account_id', back_populates='destination_account')
    monthly_balances = relationship('AccountMonthlyBalance', back_populates='account')


class AccountMonthlyBalance(Base):
    __tablename__ = 'account_monthly_balances'

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('treasury_accounts.id'), nullable=False)
    month = Column(String(7), nullable=False)  # 'YYYY-MM' e.g. '2026-08', '2026-09'
    initial_balance = Column(Float, default=0.0)

    account = relationship('TreasuryAccount', back_populates='monthly_balances')

    __table_args__ = (
        UniqueConstraint('account_id', 'month', name='uix_account_month'),
    )


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey('branches.id'), nullable=True)
    cash_register_id = Column(Integer, ForeignKey('cash_registers.id'), nullable=True)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 'INGRESO', 'EGRESO', 'TRASPASO'
    movement_type = Column(String(20), nullable=False, index=True)
    
    # Subtipos:
    # INGRESO: 'VENTA_DIARIA', 'VENTA_CALIENTE', 'COBRO_CXC', 'ABONO_CXC', 'APORTE_CAPITAL', 'PRESTAMO_RECIBIDO', 'OTRO_INGRESO'
    # EGRESO: 'GASTO_OPERATIVO', 'PAGO_PROVEEDOR', 'RETIRO_ACCIONISTA', 'PAGO_PRESTAMO', 'DEVOLUCION_VENTA', 'VALE_CAJA', 'OTRO_EGRESO'
    # TRASPASO: 'CAMBIO_DIVISAS', 'TRASPASO_CUENTAS'
    subtype = Column(String(50), nullable=False, index=True)

    account_id = Column(Integer, ForeignKey('treasury_accounts.id'), nullable=False)
    destination_account_id = Column(Integer, ForeignKey('treasury_accounts.id'), nullable=True)
    category_id = Column(Integer, ForeignKey('budget_categories.id'), nullable=True)

    amount_original = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)  # 'VES', 'USD', 'USDT'
    exchange_rate = Column(Float, default=1.0)
    amount_usd = Column(Float, nullable=False)

    reference_number = Column(String(50), nullable=True, index=True)
    beneficiary = Column(String(150), default='')
    description = Column(Text, default='')

    # Dualidad Fiscal, Cuentas por Cobrar y Abonos
    doc_type = Column(String(30), default='FACTURA_FISCAL') # 'FACTURA_FISCAL', 'NOTA_ENTREGA', 'ABONO_CXC', 'COBRO_RETENCION', 'DEVOLUCION'
    doc_number = Column(String(50), nullable=True, index=True)
    client_name = Column(String(150), nullable=True)
    client_rif = Column(String(30), nullable=True)
    
    is_credit = Column(Boolean, default=False)
    credit_status = Column(String(20), default='PAGADO') # 'PENDIENTE', 'PARCIALMENTE_PAGADO', 'PAGADO', 'ANULADO'
    credit_original_amount_usd = Column(Float, default=0.0)
    credit_balance_pending_usd = Column(Float, default=0.0)
    parent_transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    
    tax_retention_amount = Column(Float, default=0.0)
    tax_retention_proof = Column(String(50), nullable=True)
    pos_terminal = Column(String(50), nullable=True) # 'POS Banesco', 'POS Bancaribe', 'POS Banco de Venezuela', 'POS BNC'
    pos_lot_number = Column(String(30), nullable=True)
    
    # 'REGISTRADO', 'VERIFICADO', 'ANULADO'
    status = Column(String(20), default='REGISTRADO', index=True)

    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    verified_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    branch = relationship('Branch', back_populates='transactions')
    cash_register = relationship('CashRegister', back_populates='transactions')
    account = relationship('TreasuryAccount', foreign_keys=[account_id], back_populates='transactions_origin')
    destination_account = relationship('TreasuryAccount', foreign_keys=[destination_account_id], back_populates='transactions_destination')
    category = relationship('BudgetCategory', back_populates='transactions')
    creator = relationship('User', foreign_keys=[created_by_id], back_populates='transactions_created')
    verifier = relationship('User', foreign_keys=[verified_by_id], back_populates='transactions_verified')


class DailyCashClose(Base):
    __tablename__ = 'daily_cash_closes'

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey('branches.id'), nullable=True)
    cash_register_id = Column(Integer, ForeignKey('cash_registers.id'), nullable=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    cajero_name = Column(String(100), nullable=False)
    verified_by = Column(String(100), default='Administración')
    status = Column(String(20), default='CUADRADO') # 'CUADRADO', 'SOBRANTE', 'FALTANTE'
    
    # Resumen de Ventas
    profit_sales_total_usd = Column(Float, default=0.0)
    sales_fiscal_iva_usd = Column(Float, default=0.0)
    sales_notes_credit_usd = Column(Float, default=0.0)
    sales_notes_collected_usd = Column(Float, default=0.0)
    returns_total_usd = Column(Float, default=0.0)
    net_sales_usd = Column(Float, default=0.0)

    # Cobranzas y Fondos por Canal
    cash_usd_physical = Column(Float, default=0.0)
    cash_ves_physical = Column(Float, default=0.0)
    pos_total_usd = Column(Float, default=0.0)
    bank_transfers_usd = Column(Float, default=0.0)
    cashea_usd = Column(Float, default=0.0)
    retentions_iva_usd = Column(Float, default=0.0)
    retentions_islr_usd = Column(Float, default=0.0)
    expenses_caja_usd = Column(Float, default=0.0)

    total_collected_real_usd = Column(Float, default=0.0)
    total_expected_usd = Column(Float, default=0.0)
    difference_usd = Column(Float, default=0.0)
    
    # Desglose en JSON
    arqueo_usd_json = Column(Text, default='{}')
    arqueo_ves_json = Column(Text, default='{}')
    pos_details_json = Column(Text, default='{}')
    notes = Column(Text, default='')

    branch = relationship('Branch', back_populates='cash_closes')
    cash_register = relationship('CashRegister', back_populates='cash_closes')


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    rif = Column(String(30), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    bank_details = Column(Text, default='')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, index=True, nullable=False)
    value = Column(String(255), nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = Column(String(50), default='sistema')
