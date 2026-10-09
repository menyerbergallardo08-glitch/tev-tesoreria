import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

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
