# AUDITORÍA TÉCNICA TEV V2.1 — EVIDENCIAS TÉCNICAS (EVIDENCE LOG)
## Todo Eléctrico Valencia (TEV) — Sistema de Tesorería y Flujo de Caja
**Versión Auditada:** 2.1.0-Enterprise-Modular  
**Fecha:** 16 de Septiembre de 2026  

---

## 1. Evidencia por Pilar y Función

### Pilar 1: Desacoplamiento Modular
* **Archivo:** `main.py`
  * **Función:** `app.include_router(...)`
  * **Evidencia:** 10 enrutadores modulares registrados independientemente (`auth`, `sales`, `expenses`, `cxc`, `accounts`, `cash_close`, `categories`, `transfers`, `audit`, `system`).
  * **Resultado:** `VERIFIED`

### Pilar 2: Autenticación Criptográfica y RBAC
* **Archivo:** `core/security.py`
  * **Funciones:** `hash_password()`, `verify_password()`, `create_access_token()`, `get_current_user()`, `require_roles()`.
  * **Test:** `tests/test_qa_suite.py::TEST 1`
  * **Resultado:** Token expirado (12h) y token manipulado rechazados con `HTTP 401 Unauthorized`.
  * **Resultado:** `VERIFIED`

### Pilar 3: Idempotencia y Concurrencia
* **Archivo:** `services/sales_service.py` y `routers/transfers.py`
  * **Funciones:** `create_sale_transaction()`, `create_transfer()`.
  * **Mecanismo:** Bloqueo pesimista `with_for_update()` en cuentas y consulta de existencia por `doc_number` y `date`.
  * **Test:** `tests/test_qa_suite.py::TEST 3` y `tests/test_financial_regression.py::CASO 8`
  * **Salida de Ejecución:**
    `[OK] Documento duplicado bloqueado con HTTP 409 Conflict.`
    `[PASS] Transferencia ejecutada atomicamente con bloqueo pesimista y auditada.`
  * **Resultado:** `VERIFIED`

### Pilar 4: Reducción de Superficie en Producción
* **Archivo:** `main.py` (Líneas 29-35)
  * **Configuración:** `docs_url=None if IS_PRODUCTION else "/docs"`, `openapi_url=None if IS_PRODUCTION else "/openapi.json"`.
  * **Resultado:** `VERIFIED`

### Pilar 5: Cero Secretos Hardcodeados
* **Archivo:** `core/config.py`
  * **Variables:** `JWT_SECRET_KEY`, `MASTER_ADMIN_KEY`, `DATABASE_URL`, `CORS_ORIGINS`.
  * **Mecanismo:** `os.environ.get(...)` sin valores sensibles quemados en texto plano.
  * **Resultado:** `VERIFIED`

### Pilar 6: Disaster Recovery (Backup Determinístico & S3/R2)
* **Archivo:** `services/backup_service.py`
  * **Funciones:** `generate_deterministic_backup()`, `restore_deterministic_backup()`, `get_s3_config()`, `upload_to_s3_compatible()`.
  * **Formato de Archivo:** `TEV_BACKUP_YYYYMMDD_HHMMSS_<id>.json`.
  * **Test:** `tests/test_qa_suite.py::TEST 5`
  * **Salida de Ejecución:** `[OK] Backup generado: TEV_BACKUP_20260917_031702_6d363f71.json (431 registros)`.
  * **Resultado:** `VERIFIED` (Local) / `PARTIALLY VERIFIED` (S3 Remoto sujeto a variables de producción).

### Pilar 7: Gobernanza y CI/CD
* **Archivo:** `.github/workflows/ci.yml`
  * **Pipeline:** Checkout -> Python 3.12 -> Install dependencies -> Lint & Compile -> Run `test_qa_suite.py` -> Run `test_financial_regression.py`.
  * **Resultado:** `VERIFIED`

### Pilar 8: Corporate Clean Slate
* **Archivo:** `services/backup_service.py` (Líneas 160-180)
  * **Función:** `clean_slate_database()`
  * **Test:** `tests/test_financial_regression.py::CASO 9`
  * **Salida de Ejecución:** `[PASS] Clean Slate: Rechazo con 403 Forbidden verificado ante clave invalida.`
  * **Resultado:** `VERIFIED`

---

## 2. Evidencias de Lógica Financiera (9 Casos)

| Caso | Archivo de Servicio | Parámetros de Prueba | Salida Obtenida | Estado |
| :--- | :--- | :--- | :--- | :---: |
| **Venta Contado** | `services/sales_service.py` | `$100.00`, Contado | Caja = `+$100.00`, CxC = `$0.00` | `PASS` |
| **Venta Crédito Total** | `services/sales_service.py` | `$100.00`, Crédito, Abono `$0.00` | Caja = `$0.00`, CxC = `$100.00` | `PASS` |
| **Venta Crédito + Abono** | `services/sales_service.py` | `$100.00` Venta, `$30.00` Abono | Caja = `+$30.00`, CxC = `$70.00` (Cero distorsión \$130) | `PASS` |
| **Cobro CxC** | `services/cxc_service.py` | `$30.00` cobrado de saldo `$70.00` | Caja = `+$30.00`, CxC Restante = `$40.00`, Ventas = `$0` | `PASS` |
| **Deuda Histórica Onboarding** | `services/cxc_service.py` | `$500.00`, Fecha: `2026-07-01` | Ventas de hoy = `$0.00`, Caja = `$0.00`, CxC = `$500.00` | `PASS` |
| **Cobro Deuda Histórica** | `services/cxc_service.py` | `$200.00` abonados hoy | Caja hoy = `+$200.00`, Ventas hoy = `$0.00`, CxC = `$300.00` | `PASS` |
| **Gasto + Retención SENIAT** | `services/expense_service.py` | `$150.00` Gasto, `$18.00` Retención | Comprobante normalizado: `20260900000045` (14 dígitos) | `PASS` |
| **Transferencia Interbancaria** | `routers/transfers.py` | `$50.00` de Acc1 a Acc2 | Bloqueo pesimista en ambas cuentas + Registro de Traspaso | `PASS` |
| **Clean Slate Protegido** | `services/backup_service.py` | `master_key = 'CLAVE_INCORRECTA'` | Retorna `HTTP 403 Forbidden` | `PASS` |
