import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base

class BudgetCategory(Base):
    __tablename__ = 'budget_categories'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    monthly_budget_usd = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    transactions = relationship('Transaction', back_populates='category')


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    rif = Column(String(30), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    bank_details = Column(Text, default='')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
