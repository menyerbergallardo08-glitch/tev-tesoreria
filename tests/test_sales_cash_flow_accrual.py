from decimal import Decimal, ROUND_HALF_UP
import pytest
from unittest.mock import MagicMock

# Ajusta las importaciones según la ruta de tu proyecto
from services.sales_service import process_sale
from models.transaction import TransactionType, PaymentMethod


CENT = Decimal("0.01")


def round_curr(value: Decimal) -> Decimal:
    """Redondeo financiero estándar a 2 decimales."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@pytest.fixture
def mock_db():
    """Simula la sesión de base de datos SQLAlchemy."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.flush = MagicMock()
    return session


@pytest.fixture
def base_bcv_rate():
    """Tasa BCV de prueba con precisión decimal completa."""
    return Decimal("52.8450")


# ============================================================================
# 1. PRUEBAS DE SEPARACIÓN: FLUJO DE CAJA VS. DEVENGO
# ============================================================================

def test_sale_100_percent_cash(mock_db, base_bcv_rate):
    """
    Venta de contado estricta:
    - Devengo = 100% de la venta
    - Flujo de caja = 100% ingresado en tesorería
    - Cartera CxC = 0.00
    """
    payload = {
        "client_name": "Inversiones Eléctricas C.A.",
        "amount_usd": Decimal("250.00"),
        "payment_method": PaymentMethod.TRANSFER_USD,
        "is_credit": False,
        "cash_received_usd": Decimal("250.00"),
        "account_id": 1,
        "bcv_rate": base_bcv_rate,
    }

    result = process_sale(mock_db, payload)

    assert result.accrued_revenue_usd == Decimal("250.00"), "El devengo debe ser el total facturado"
    assert result.cash_flow_impact_usd == Decimal("250.00"), "El flujo de caja debe registrar el ingreso total"
    assert result.cxc_generated_usd == Decimal("0.00"), "No debe generarse cuenta por cobrar"
    assert result.accrued_revenue_usd == result.cash_flow_impact_usd + result.cxc_generated_usd


def test_sale_100_percent_credit(mock_db, base_bcv_rate):
    """
    Venta a crédito total:
    - Devengo = 100% de la venta
    - Flujo de caja = 0.00 (no hay impacto en cuentas bancarias)
    - Cartera CxC = 100% pendiente de cobro
    """
    payload = {
        "client_name": "Contratista Valencia",
        "amount_usd": Decimal("1200.00"),
        "payment_method": PaymentMethod.CREDIT_NOTE,
        "is_credit": True,
        "cash_received_usd": Decimal("0.00"),
        "account_id": None,
        "bcv_rate": base_bcv_rate,
    }

    result = process_sale(mock_db, payload)

    assert result.accrued_revenue_usd == Decimal("1200.00")
    assert result.cash_flow_impact_usd == Decimal("0.00"), "El flujo de caja debe ser 0 en ventas a crédito puro"
    assert result.cxc_generated_usd == Decimal("1200.00"), "Toda la venta debe transferirse a CxC"
    assert result.accrued_revenue_usd == result.cash_flow_impact_usd + result.cxc_generated_usd


def test_sale_mixed_cashea_down_payment(mock_db, base_bcv_rate):
    """
    Venta mixta / modelo Cashea:
    - Total: $150.00
    - Inicial mostrador (40%): $60.00 en efectivo
    - Saldo financiado (60%): $90.00 en cartera diferida
    """
    total = Decimal("150.00")
    initial_cash = Decimal("60.00")
    credit_portion = Decimal("90.00")

    payload = {
        "client_name": "Cliente Cashea Nivel 1",
        "amount_usd": total,
        "payment_method": PaymentMethod.CASHEA_SPLIT,
        "is_credit": True,
        "cash_received_usd": initial_cash,
        "account_id": 2,  # Caja Chica USD
        "bcv_rate": base_bcv_rate,
    }

    result = process_sale(mock_db, payload)

    assert result.accrued_revenue_usd == total
    assert result.cash_flow_impact_usd == initial_cash
    assert result.cxc_generated_usd == credit_portion
    # Invariante contable
    assert result.accrued_revenue_usd == (result.cash_flow_impact_usd + result.cxc_generated_usd)


# ============================================================================
# 2. CASOS BORDE: REDONDEO BIMONETARIO Y TASA FLOTANTE BCV
# ============================================================================

@pytest.mark.parametrize("bcv_rate, amount_usd, expected_bs", [
    (Decimal("52.8450"), Decimal("33.33"), Decimal("1761.32")),
    (Decimal("53.1119"), Decimal("19.99"), Decimal("1061.71")),
    (Decimal("50.0001"), Decimal("0.01"), Decimal("0.50")),
])
def test_bcv_conversion_no_floating_point_leak(mock_db, bcv_rate, amount_usd, expected_bs):
    """
    Verifica que la conversión USD -> Bs no utilice punto flotante binario (IEEE 754)
    y preserve la precisión requerida para auditoría SENIAT.
    """
    payload = {
        "client_name": "Venta Fiscal Mostrador",
        "amount_usd": amount_usd,
        "payment_method": PaymentMethod.PAGO_MOVIL_BS,
        "is_credit": False,
        "cash_received_usd": amount_usd,
        "account_id": 3,  # Banco BNC Bs
        "bcv_rate": bcv_rate,
    }

    result = process_sale(mock_db, payload)

    raw_bs = amount_usd * bcv_rate
    rounded_bs = round_curr(raw_bs)

    assert result.amount_ves == expected_bs
    assert result.amount_ves == rounded_bs


def test_split_currency_rounding_drift(mock_db):
    """
    Caso de pago mixto ($ en efectivo + Bs en Punto de Venta):
    - Total: $100.00
    - Pago 1: $45.00 en efectivo
    - Pago 2: Restante $55.00 pagados en Bs a tasa 52.8450 -> Bs. 2.906,475 -> 2.906,48 Bs
    - Reconversión a USD no debe generar centavos fantasma ($99.99 o $100.01).
    """
    rate = Decimal("52.8450")
    total_usd = Decimal("100.00")
    cash_usd = Decimal("45.00")
    remaining_usd = Decimal("55.00")

    # Pago en Bs redondeado al centavo más cercano
    ves_paid = round_curr(remaining_usd * rate)  # 2906.48 Bs
    recalculated_usd = round_curr(ves_paid / rate)  # 55.00 USD

    payload = {
        "client_name": "Cliente Mostrador Multimoneda",
        "amount_usd": total_usd,
        "payment_method": PaymentMethod.MIXED_USD_VES,
        "is_credit": False,
        "payments": [
            {"currency": "USD", "amount": cash_usd, "account_id": 1},
            {"currency": "VES", "amount": ves_paid, "account_id": 4, "bcv_rate": rate},
        ],
        "bcv_rate": rate,
    }

    result = process_sale(mock_db, payload)

    total_settled_usd = cash_usd + recalculated_usd

    # La diferencia máxima tolerada por conversión cruzada es 0.01 USD
    discrepancy = abs(result.accrued_revenue_usd - total_settled_usd)
    assert discrepancy <= Decimal("0.01"), f"Discrepancia por redondeo fuera de rango: {discrepancy}"
    assert result.cash_flow_impact_usd == total_usd


# ============================================================================
# 3. CONTROL DE INTEGRIDAD Y RECHAZOS (DEFENSIVE PROGRAMMING)
# ============================================================================

def test_reject_sale_negative_or_zero_amount(mock_db, base_bcv_rate):
    """El servicio debe rechazar transacciones con importe cero o negativo."""
    payload = {
        "client_name": "Error de Terminal",
        "amount_usd": Decimal("-5.00"),
        "payment_method": PaymentMethod.CASH_USD,
        "is_credit": False,
        "bcv_rate": base_bcv_rate,
    }

    with pytest.raises(ValueError, match="El monto de la venta debe ser mayor a cero"):
        process_sale(mock_db, payload)


def test_reject_cash_flow_exceeding_accrued_revenue(mock_db, base_bcv_rate):
    """El cobro inicial no puede exceder el devengo total sin crear un anticipo explícito."""
    payload = {
        "client_name": "Sobrecobro Mostrador",
        "amount_usd": Decimal("50.00"),
        "payment_method": PaymentMethod.CASH_USD,
        "is_credit": False,
        "cash_received_usd": Decimal("60.00"),  # Error de digitación
        "account_id": 1,
        "bcv_rate": base_bcv_rate,
    }
    with pytest.raises(ValueError, match="El flujo de caja recibido no puede exceder el total de la venta"):
        process_sale(mock_db, payload)
