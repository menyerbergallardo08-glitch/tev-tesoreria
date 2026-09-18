# DÍA 7 — SIMULACIÓN INTEGRAL DE JORNADA Y CIERRE DE CICLO
## Laboratorio Operacional TEV (7 Días)

### Objetivo
Ejecutar una simulación continua de punta a punta de 8 horas comerciales (apertura, ventas, cobros, transferencias, egresos, retenciones y cuadre de caja).

### Escenarios a Ejecutar
1. **Apertura de Turno**: Verificación matutina de cuentas.
2. **Ciclo Comercial Continuo**: Múltiples ventas de contado, crédito y abonos simultáneos.
3. **Gestión de Tesorería**: Pago de gastos y conciliación bancaria.
4. **Cierre de Caja y Snapshot**: Ejecutar el cuadre diario final y generar snapshot de respaldo en Cloudflare R2.

### Criterio de Éxito
- Cuadre matemático exacto entre ingresos, egresos y saldos en bóveda/bancos.
