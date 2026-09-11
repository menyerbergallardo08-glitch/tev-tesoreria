# 👩‍💼 MANUAL OPERATIVO DEL USUARIO: CAJERA
## Sistema de Facturación, Cobro Multicanal y Arqueo Diario
### **TODO ELÉCTRICO VALENCIA, C.A.**

---

## 🎯 OBJETIVO DEL ROL
Garantizar el registro exacto de cada venta en mostrador (Contado, Cashea o Crédito), la correcta retención de impuestos cuando aplique (Normativa SENIAT 14 dígitos), y el arqueo físico y cierre diario de caja sin discrepancias.

---

## 1. ⚡ FACTURACIÓN Y COBRANZA MULTICANAL

### A. Venta de Contado Directo
1. Ingrese a la pestaña **`⚡ Facturación y Punto de Venta`**.
2. Seleccione el **Tipo de Documento**: `Factura Fiscal` o `Nota de Entrega`.
3. Ingrese el **N° de Documento** (ej: `FAC-00892` o `NE-0145`).
4. Ingrese el **Nombre del Cliente** y su **RIF / Cédula**.
5. En **Monto**, digite el total y seleccione la moneda (**USD $** o **VES Bs.**).
6. Seleccione la **Modalidad**: `💵 Contado Inmediato`.
7. **Seleccione la Vía de Cobro:**
   - **Efectivo USD:** Para billetes en divisas recibidos en gaveta.
   - **Efectivo VES:** Para billetes en bolívares recibidos en gaveta.
   - **Punto de Venta (POS):** Elija *POS Banesco*, *POS Bancaribe*, *POS BDV* o *POS BNC*.
     > ⚠️ **IMPORTANTE:** Al cobrar por punto, ingrese siempre el **N° de Lote** (ej: `0234`) del comprobante físico del punto de venta.
   - **Pago Móvil / Transferencia:** Ingrese el **N° de Referencia Bancaria** (últimos 6 u 8 dígitos).
8. Presione **`💾 Registrar Venta / Cobro`**.

---

### B. Venta con Aplicación Cashea (Inicial en Tienda + Saldo BNC)
1. En la pantalla de Facturación, ingrese el documento, cliente y el **Monto Total** (ej: `$100.00`).
2. En Modalidad, marque **`🟡 Crédito / Financiamiento`**.
3. Active la casilla: **`🟡 Venta con Cashea (Cobro de Inicial en Tienda + Saldo a BNC)`**.
4. Seleccione el **% de Inicial** según el nivel del cliente en su App Cashea (`40%`, `50%` o `60%`).
5. Indique por dónde está pagando el cliente la inicial (ej: *POS Banesco* o *Efectivo USD*).
6. Verifique el desglose en pantalla:
   - 💵 **En Caja Tienda hoy:** `$50.00`
   - 🟡 **Saldo a cobrar a Cashea:** `$50.00`
7. Presione **`💾 Registrar Venta Cashea`**.

---

### C. Venta a Crédito Corporativo (CxC Clientes)
1. Seleccione `Factura Fiscal` o `Nota de Entrega`.
2. Ingrese los datos de la empresa cliente y el monto.
3. Marque **`🟡 Crédito / Financiamiento`** (sin marcar Cashea).
4. Si el cliente dejó un anticipo hoy en tienda, colóquelo en **Abono Inicial** y seleccione la caja receptora. Si no dejó abono, deje en `$0.00`.
5. Presione **`💾 Guardar Venta a Crédito en CxC`**.

---

## 2. 🏛️ RETENCIONES SENIAT (EXCLUSIVO FACTURAS FISCALES)

> ⚠️ Las retenciones de IVA / ISLR solo aplican cuando el documento es **Factura Fiscal** y el cliente es **Contribuyente Especial**. No aplican para Notas de Entrega.

1. Seleccione **`Factura Fiscal`** en el tipo de documento.
2. Active la casilla: **`¿El cliente entregó Comprobante de Retención IVA / ISLR?`**.
3. **Calcular Porcentaje con 1 Clic:**
   - Presione **`🏛️ 75% IVA (Estándar)`** o **`🏛️ 100% IVA (Total)`**.
   - El sistema calcula el monto exacto y el **Neto Real que el cliente debe cancelar**.
4. **Cargar el Número de Comprobante (14 Dígitos):**
   - Ingrese el comprobante entregado (ej: `20260900000045` o `2026-09-45`).
   - El sistema verificará que contenga exactamente **14 dígitos numéricos** (`AAAAMMCCCCCCCC`) y mostrará la insignia verde: **`✓ 14 DÍGITOS OK`**.
5. Cobre el neto restante y guarde la venta.

---

## 3. 🔄 DEVOLUCIONES Y REEMBOLSOS

1. Seleccione en Tipo de Documento: **`DEVOLUCIÓN / NOTA DE CRÉDITO`**.
2. Ingrese el número de la factura original y el nombre del cliente.
3. Ingrese el monto a devolver.
4. **Seleccione la Modalidad de Devolución:**
   - `Efectivo USD / VES (Gaveta)`: Sale dinero físico de la caja.
   - `Reverso Punto de Venta`: Ingrese el N° de lote donde se hizo el reverso.
   - `Saldo a Favor / Nota de Crédito`: No sale dinero físico de la caja.
5. Presione **`Procesar Devolución en Caja`**.

---

## 4. 🔒 ARQUEO FÍSICO Y CIERRE DIARIO DE CAJA (1 HOJA)

Al finalizar la jornada (5:00 PM - 5:30 PM):

1. Diríjase a la pestaña **`🔒 Arqueo & Cuadre Diario`**.
2. **Conteo Físico en Dólares ($):**
   - Cuente los billetes de la gaveta e ingrese las cantidades en cada casilla: `$100`, `$50`, `$20`, `$10`, `$5`, `$1`.
3. **Conteo Físico en Bolívares (Bs.):**
   - Cambie la pestaña a Bolívares e ingrese los billetes de `Bs. 500`, `Bs. 200`, `Bs. 100`, etc.
4. **Validación de Cuadre:**
   - El sistema comparará su dinero contado contra las ventas registradas.
   - Debe indicar: **`DIFERENCIA: $0.00 | CAJA CUADRADA PERFECTA 🟢`**.
5. **Impresión del Comprobante:**
   - Presione el botón **`📄 Ver Comprobante (1 Hoja)`**.
   - Revise el resumen ejecutivo en pantalla y presione **`🖨️ Imprimir Comprobante`**.
   - Firme el comprobante junto con la Administradora y anéxelo al sobre de efectivo.
