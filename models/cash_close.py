import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class DailyCashClose(Base):
    __tablename__ = 'daily_cash_closes'

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey('branches.id'), nullable=True)
    cash_register_id = Column(Integer, ForeignKey('cash_registers.id'), nullable=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    cajero_name = Column(String(100), nullable=False)
    verified_by = Column(String(100), default='Administración')
    status = Column(String(20), default='CUADRADO')
    
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
    
    arqueo_usd_json = Column(Text, default='{}')
    arqueo_ves_json = Column(Text, default='{}')
    pos_details_json = Column(Text, default='{}')
    notes = Column(Text, default='')

    branch = relationship('Branch', back_populates='cash_closes')
    cash_register = relationship('CashRegister', back_populates='cash_closes')
