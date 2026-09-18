# INVENTARIO FUNCIONAL DETALLADO (V3.1)
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

---

| ID | Módulo | Funcionalidad | Usuario Responsable | Entrada | Proceso | Resultado Esperado | Dependencias | Riesgos | Estado Actual |
|---|---|---|---|---|---|---|---|---|---|
| **F-01** | Autenticación | Login con JWT y RBAC | Todos | Usuario / Contraseña | Validación Bcrypt + Firma HS256 | Token Bearer emitido (12h) | `models.User` | Bloqueo por expiración | OPERATIVO |
| **F-02** | Autenticación | Perfil `/api/auth/me` | Autenticado | Token en Header | Decodificación y consulta SQL | Datos de usuario y rol | JWT | Manipulación de token | OPERATIVO |
| **F-03** | Cajas/Bancos | Listado de Cuentas | Todos | Ninguna | Consulta SQL con flag inactivos | Array JSON de cuentas | `models.TreasuryAccount` | Consulta no filtrada | OPERATIVO |
| **F-04** | Cajas/Bancos | Crear/Editar Cuenta | Administradora / Directivo | Nombre, moneda, tipo | Inserción en DB + Auditoría | Nueva cuenta activa | `models.TreasuryAccount` | Duplicidad de nombre | OPERATIVO |
| **F-05** | Cajas/Bancos | Soft Delete de Cuentas | Administradora / Directivo | `account_id` | Toggle `is_active` | Inhabilitación sin borrado físico | Cuentas | Cuentas con saldo vivo | OPERATIVO |
| **F-06** | Ventas | Venta de Contado | Cajera / Admin | Monto, cuenta, cliente, doc | Inserción atómica + suma saldo | Saldo cuenta incrementado | Cuentas activas | Documento duplicado (409) | OPERATIVO |
| **F-07** | Ventas | Venta a Crédito Total | Cajera / Admin | Monto, cliente, RIF, doc | Creación Tx Crédito ($0 caja) | CxC creada, Caja intacta | `models.Transaction` | Descuadre en caja | OPERATIVO |
| **F-08** | Ventas | Venta Crédito + Abono | Cajera / Admin | Venta $100, Abono $30 | Caja +$30, Venta $100, CxC $70 | Separación flujo vs devengo | Cuentas activas | Distorsión de $130 (Evitada) | OPERATIVO |
| **F-09** | Ventas | Anulación de Venta | Administradora / Directivo | `transaction_id`, motivo | Marcado `ANULADO` + reversión | Saldo revertido + Auditoría | Auditoría | Re-anulación bloqueada | OPERATIVO |
| **F-10** | CxC | Listar Deudas Pendientes | Administradora / Directivo | Filtro estado (ALL/PENDING) | Consulta SQL sobre `is_credit` | Lista de clientes morosos | Ventas a crédito | Lectura desactualizada | OPERATIVO |
| **F-11** | CxC | Cobro / Abono de CxC | Cajera / Admin | `parent_id`, monto, cuenta | Abono atómico a deuda | CxC disminuye, Caja sube | Deuda existente | Sobrepago (> pendiente) | OPERATIVO |
| **F-12** | CxC | Deuda Histórica Onboarding| Administradora / Directivo | Cliente, saldo heredado | Registro en CxC sin venta actual | CxC cargada ($0 caja, $0 venta)| Ninguna | Falsa venta actual | OPERATIVO |
| **F-13** | Egresos | Registro de Gasto | Administradora / Directivo | Beneficiario, monto, cuenta | Egreso atómico + resta saldo | Saldo cuenta decrementado | Saldo disponible | Saldo negativo no alertado | OPERATIVO |
| **F-14** | Egresos | Retención SENIAT | Administradora / Directivo | Base, % IVA, comprobante 14d | Validación 14 dígitos + egreso | Retención registrada | Parámetros fiscales | Formato no estándar (Bloqueado) | OPERATIVO |
| **F-15** | Transferencias | Traspaso entre Cuentas | Administradora / Directivo | Cuenta origen, destino, monto | Bloqueo pesimista (-A, +B) | Total consolidado idéntico | Cuentas activas | Creación ficticia de fondos | OPERATIVO |
| **F-16** | Cierre Caja | Resumen Diario | Cajera / Admin | Fecha de consulta | Agrupación SQL por forma pago | Total recaudado desglosado | Transacciones del día| Transacciones huérfanas | OPERATIVO |
| **F-17** | Sistema/DR | Backup Deterministico | Directivo / Admin | Token JWT | Generación JSON + SHA256 + R2 | Archivo remoto en Cloudflare | Boto3 / R2 Bucket | Fallo de red / timeout | OPERATIVO |
| **F-18** | Gobernanza | Tasa Oficial BCV | Todos | Consulta | Resolución con fallback fin sem | Tasa Bs./USD oficial | Cache / BCV API | Desactualización de tasa | OPERATIVO |
