# DÍA 3 — EGRESOS, PROVEEDORES Y RETENCIONES SENIAT
## Laboratorio Operacional TEV (7 Días)

### Objetivo
Validar la emisión de pagos a proveedores y la retención fiscal SENIAT de 14 dígitos.

### Escenarios a Ejecutar
1. **Gasto Operativo**: Pago de servicio menor (ej. $20 en efectivo).
2. **Pago a Proveedor con Retención SENIAT**: Pago de $200 a proveedor con comprobante SENIAT de 14 dígitos (ej. `20260900000123`).
3. **Validación de Rechazo**: Intentar registrar un comprobante de 10 dígitos y comprobar que el sistema lo rechace.

### Criterio de Éxito
- Formato fiscal validado con éxito.
- Egreso descontado con precisión de la cuenta origen.
