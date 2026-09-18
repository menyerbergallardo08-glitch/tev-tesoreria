# DÍA 5 — GESTIÓN DE EXCEPCIONES Y ERRORES HUMANOS
## Laboratorio Operacional TEV (7 Días)

### Objetivo
Someter deliberadamente al sistema a errores típicos de operadoras para evaluar la robustez de los bloqueos y mensajes de error.

### Escenarios a Ejecutar
1. **Doble Clic Rápido**: Enviar dos veces seguidas la misma venta con el mismo número de factura $\rightarrow$ Bloqueo HTTP 409 Conflict.
2. **Cobro Mayor a Deuda**: Intentar cobrar $150 a una deuda de $100 $\rightarrow$ Bloqueo controlado.
3. **Monto Negativo o Cero**: Intentar registrar egreso de -$50 $\rightarrow$ Bloqueo de validación 422.
4. **Anulación de Venta**: Anular una venta por error de digitación $\rightarrow$ Verificación de reversión de saldo y auditoría inmutable.

### Criterio de Éxito
- Integridad financiera 100% blindada.
- Mensajes claros al usuario.
