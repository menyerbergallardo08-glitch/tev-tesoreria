# MATRIZ DE OBSERVACIÓN OPERATIVA DE CAMPO (V3.1)
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

---

### Estructura de Registro para el Piloto de 7 Días

| ID | Día | Módulo | Proceso | Usuario | Escenario Simulado | Resultado Esperado | Resultado Observado | ¿Funciona? | ¿Es Intuitivo? | ¿Es Rápido? | ¿Existe Riesgo? | Severidad | Recomendación / Acción | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **OBS-01** | DÍA 1 | Apertura | Consulta de saldos | Cajera | Inicio de jornada y verificación de cuentas | Cuentas en cero identificables | Panel carga 10 cuentas | SÍ | SÍ | SÍ (<1s) | BAJO | P3 | Mantener indicador de modo laboratorio | PREPARADO |
| **OBS-02** | DÍA 2 | Ventas | Venta Contado + Crédito | Cajera | Venta mixta con anticipo | Flujo de caja = anticipo, CxC = resto | Lógica matemática validada | SÍ | SÍ | SÍ | BAJO | P2 | Añadir botón de impresión rápida de recibo | PREPARADO |
| **OBS-03** | DÍA 2 | CxC | Cobro de Deuda | Cajera | Cliente paga saldo pendiente de factura | Reducción de CxC sin duplicar venta | Disminución atómica de saldo | SÍ | SÍ | SÍ | BAJO | P3 | Notificación visual de deuda saldada | PREPARADO |
| **OBS-04** | DÍA 3 | Egresos | Gasto con Retención | Admin | Pago a proveedor con SENIAT 14 dígitos | Formato estricto validado en backend | Rechazo si no tiene 14 dígitos | SÍ | SÍ | SÍ | MEDIO | P2 | Ayuda visual / máscara en input SENIAT | PREPARADO |
| **OBS-05** | DÍA 4 | Tesorería | Transferencia Banco a Caja | Admin | Traspaso de divisas a caja física | Origen disminuye, destino aumenta | Consolidado constante | SÍ | SÍ | SÍ | BAJO | P3 | Selector con autocompletado de cuenta | PREPARADO |
| **OBS-06** | DÍA 5 | Seguridad | Inyección y Duplicados | Tester | Doble click rápido en formulario | HTTP 409 Conflict anti-duplicado | Idempotencia garantizada | SÍ | SÍ | SÍ | NINGUNO | P3 | Deshabilitar botón tras 1er click en UI | PREPARADO |
| **OBS-07** | DÍA 6 | Reportes | Cuadre de Caja Diario | Admin | Auditoría de cobros vs gaveta física | Total desglosado por moneda/caja | Resumen consolidado disponible | SÍ | SÍ | SÍ | BAJO | P2 | Exportación a PDF / Excel de cierre | PREPARADO |
| **OBS-08** | DÍA 7 | Cierre | Jornada Integral Completa | Admin | Flujo punta a punta de 8 horas | Consistencia contable total | Cero descuadres detectados | SÍ | SÍ | SÍ | BAJO | P2 | Snapshot automático en R2 al cerrar | PREPARADO |
