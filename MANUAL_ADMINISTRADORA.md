# 👩‍💻 MANUAL OPERATIVO DEL USUARIO: ADMINISTRADORA
## Sistema de Tesorería Central, Cuentas por Cobrar, Egresos y Conciliación
### **TODO ELÉCTRICO VALENCIA, C.A.**

---

## 🎯 OBJETIVO DEL ROL
Gestionar la liquidez global de la empresa, conciliar los puntos de venta con los estados de cuenta bancarios, cobrar la cartera de clientes y liquidar los lotes de Cashea (BNC), programar pagos a proveedores e impuestos, y auditar el cierre de caja diario.

---

## 1. 📡 MONITOR EN VIVO Y CONCILIACIÓN DE LOTES DE PUNTOS DE VENTA (POS)

1. Ingrese a la pestaña **`📡 Monitor de Caja en Vivo`**.
2. **Auditoría de Puntos de Venta:**
   - Compare los reportes de cierre de lote físico emitidos por los puntos (*Banesco, Bancaribe, BDV, BNC*) contra los totales por terminal que reporta el sistema en la tarjeta **💳 Lotes POS**.
3. **Validación de Pago Móvil y Transferencias:**
   - Verifique en la banca en línea que las referencias bancarias cargadas por la cajera coincidan exactamente en monto y beneficiario.

---

## 2. 📋 GESTIÓN DE CUENTAS POR COBRAR (CxC)

El sistema divide la cartera de crédito en dos secciones especializadas:

### A. Cartera de Clientes Corporativos (`👥 CxC Clientes`)
1. Ingrese a **`📋 Cuentas por Cobrar (CxC)`** y seleccione **`👥 CxC Clientes`**.
2. Revise el listado de documentos pendientes y su antigüedad.
3. **Para registrar un Abono o Cancelación Total:**
   - Presione el botón verde **`💵 Abonar`** en la factura correspondiente.
   - Ingrese la **Fecha del Pago**, el **Monto Abonado** y la **Cuenta Bancaria Receptora**.
   - Digite el **N° de Referencia Bancaria**.
   - Si el cliente aplicó retención adicional en este pago, ingrese el monto y el comprobante de 14 dígitos.
   - Presione **`💾 Registrar Abono`**.
   - El sistema actualizará el saldo pendiente y cambiará el estatus a `PARCIALMENTE_PAGADO` o `PAGADO`.

### B. Cartera Cashea (`🟡 CxC Cashea - BNC`)
1. En **`📋 Cuentas por Cobrar (CxC)`**, haga clic en **`🟡 CxC Cashea (BNC)`**.
2. Verá todas las ventas efectuadas por Cashea con su saldo pendiente por liquidar.
3. **Para liquidar las transferencias recibidas de Cashea:**
   - Al verificar el crédito semanal en la cuenta BNC, seleccione las órdenes correspondientes y presione **`💵 Liquidar Lote Cashea`**.
   - Ingrese la referencia bancaria del BNC y guarde la liquidación.

---

## 3. 📤 GASTOS OPERATIVOS Y PAGOS A PROVEEDORES

1. Ingrese a **`📤 Egresos y Cuentas por Pagar`**.
2. **Pagos a Proveedores:**
   - Seleccione `PAGO_PROVEEDOR`, indique el nombre del proveedor, cuenta de origen, referencia bancaria y monto.
3. **Gastos Operativos (Obligatorio con Partida):**
   - Seleccione `GASTO_OPERATIVO`.
   - **Seleccione la Partida Presupuestaria:** (ej: *Nómina, Mantenimiento, Servicios Públicos, Suministros de Oficina, Fletes*).
   - Ingrese el beneficiario, descripción detallada y comprobante de egreso.
   - Presione **`Guardar Egreso`**.

---

## 4. 🔄 TRASPASOS ENTRE CUENTAS Y OPERACIONES DE CAMBIO

1. Vaya a **`🔄 Traspasos / Movimientos Especiales`**.
2. Para cambiar dólares en efectivo y depositarlos en bolívares en el banco:
   - **Cuenta Origen:** *Efectivo USD (Caja Tienda)*.
   - **Cuenta Destino:** *Banesco VES* (o banco receptor).
   - Ingrese el monto en divisas entregado y la tasa pactada.
   - Ingrese el número de depósito bancario.
   - Presione **`Ejecutar Traspaso Contable`**.
   - El sistema genera el doble asiento contable instantáneamente.

---

## 5. 🇻🇪 TASA OFICIAL BCV Y MANTENIMIENTO

* El sistema consulta automáticamente la web oficial `bcv.org.ve` cada 3 minutos.
* Si el portal del Banco Central presenta indisponibilidad, presione el botón superior **`🇻🇪 BCV`** e introduzca la tasa oficial confirmada para mantener todas las cajas sincronizadas.
