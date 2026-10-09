from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

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
    month = Column(String(7), nullable=False)  # 'YYYY-MM'
    initial_balance = Column(Float, default=0.0)

    account = relationship('TreasuryAccount', back_populates='monthly_balances')

    __table_args__ = (
        UniqueConstraint('account_id', 'month', name='uix_account_month'),
    )
