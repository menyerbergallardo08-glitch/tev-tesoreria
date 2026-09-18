# DÍA 2 — VENTAS, CRÉDITOS Y COBRANZAS (CxC)
## Laboratorio Operacional TEV (7 Días)

### Objetivo
Validar el registro de ventas de contado, ventas mixtas a crédito con anticipo, y cobros posteriores de cuentas por cobrar.

### Escenarios a Ejecutar
1. **Venta Contado**: Registrar venta de $50 pagada en Efectivo USD.
2. **Venta a Crédito con Abono**: Registrar venta de $100 con abono inicial de $30 en Punto de Venta Banesco y saldo restante $70 a crédito.
3. **Consulta de CxC**: Verificar que el cliente figure en el listado de morosos con $70 pendientes.
4. **Cobro Posterior**: Abonar $40 a la deuda y comprobar que el saldo pendiente baje a $30.

### Criterio de Éxito
- Cero distorsión contable ($30 entran a caja, $100 se reconocen como venta, $70 en CxC).
