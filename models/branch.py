import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class Branch(Base):
    __tablename__ = 'branches'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
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
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    branch = relationship('Branch', back_populates='cash_registers')
    transactions = relationship('Transaction', back_populates='cash_register')
    cash_closes = relationship('DailyCashClose', back_populates='cash_register')

    __table_args__ = (
        UniqueConstraint('branch_id', 'code', name='uix_branch_cash_register_code'),
    )
