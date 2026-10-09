import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(50), nullable=False, default='sistema')
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(50), nullable=True)
    details_json = Column(Text, default='{}')
    ip_address = Column(String(50), default='')

    user = relationship('User', back_populates='audit_logs')


class SystemSetting(Base):
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, index=True, nullable=False)
    value = Column(String(255), nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = Column(String(50), default='sistema')
