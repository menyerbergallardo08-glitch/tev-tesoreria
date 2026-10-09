import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class TransactionType(str, Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"
    TRASPASO = "TRASPASO"

class PaymentMethod(str, Enum):
    CASH_USD = "CASH_USD"
    TRANSFER_USD = "TRANSFER_USD"
    CREDIT_NOTE = "CREDIT_NOTE"
    CASHEA_SPLIT = "CASHEA_SPLIT"
    PAGO_MOVIL_BS = "PAGO_MOVIL_BS"
    MIXED_USD_VES = "MIXED_USD_VES"
    EFECTIVO_USD = "EFECTIVO_USD"
    EFECTIVO_VES = "EFECTIVO_VES"
    PUNTO_VENTA = "PUNTO_VENTA"
    TRANSFERENCIA = "TRANSFERENCIA"
    ZELLE = "ZELLE"
    USDT = "USDT"

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey('branches.id'), nullable=True)
    cash_register_id = Column(Integer, ForeignKey('cash_registers.id'), nullable=True)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 'INGRESO', 'EGRESO', 'TRASPASO'
    movement_type = Column(String(20), nullable=False, index=True)
    
    # Subtipos
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

    # Dualidad Fiscal y CxC
    doc_type = Column(String(30), default='FACTURA_FISCAL')
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
    pos_terminal = Column(String(50), nullable=True)
    pos_lot_number = Column(String(30), nullable=True)
    
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
