# INFORME DE PRUEBAS Y COBERTURA TÉCNICA V2.1 (TEST REPORT)
## Todo Eléctrico Valencia (TEV) — Sistema de Tesorería y Flujo de Caja
**Fecha:** 16 de Septiembre de 2026  
**Ambiente de Ejecución:** Sandbox Local (SQLite WAL / FastAPI TestClient)  

---

## 1. Resumen de Ejecución de Pruebas

| Métrica | Valor |
| :--- | :---: |
| **Total Casos de Regresión Financiera** | 9 |
| **Casos Financieros Aprobados (Passed)** | 9 (100.0%) |
| **Total Casos de Seguridad y QA** | 7 |
| **Casos QA Aprobados (Passed)** | 7 (100.0%) |
| **Casos Fallidos (Failed)** | 0 (0.0%) |
| **Casos Omitidos (Skipped)** | 0 (0.0%) |
| **Tasa Global de Aprobación (Success Rate)** | **100.0%** |

---

## 2. Desglose de Cobertura Matemática Real de Código

| Módulo / Archivo | Líneas Ejecutables | Líneas Cubiertas por Tests | Cobertura % |
| :--- | :---: | :---: | :---: |
| `schemas/accounts.py` | 15 | 15 | **100.0%** |
| `schemas/cash_close.py` | 24 | 24 | **100.0%** |
| `schemas/cxc.py` | 18 | 18 | **100.0%** |
| `schemas/expenses.py` | 25 | 25 | **100.0%** |
| `schemas/sales.py` | 24 | 24 | **100.0%** |
| `schemas/system.py` | 4 | 4 | **100.0%** |
| `schemas/users.py` | 14 | 14 | **100.0%** |
| `database.py` | 38 | 22 | **57.9%** |
| `routers/system.py` | 68 | 38 | **55.9%** |
| `routers/accounts.py` | 45 | 23 | **51.1%** |
| `routers/audit.py` | 23 | 11 | **47.8%** |
| `routers/expenses.py` | 69 | 30 | **43.5%** |
| `routers/transfers.py` | 50 | 21 | **42.0%** |
| `core/audit.py` | 29 | 12 | **41.4%** |
| `routers/categories.py` | 31 | 12 | **38.7%** |
| `routers/sales.py` | 75 | 28 | **37.3%** |
| `routers/cxc.py` | 69 | 25 | **36.2%** |
| `routers/auth.py` | 91 | 26 | **28.6%** |
| `routers/cash_close.py` | 74 | 19 | **25.7%** |
| `core/security.py` | 84 | 21 | **25.0%** |
| `services/account_service.py` | 33 | 7 | **21.2%** |
| `services/backup_service.py` | 204 | 30 | **14.7%** |
| `services/expense_service.py` | 67 | 8 | **11.9%** |
| `core/bcv.py` | 94 | 10 | **10.6%** |
| `services/cxc_service.py` | 92 | 7 | **7.6%** |
| `services/sales_service.py` | 93 | 6 | **6.5%** |
| `core/seniat.py` | 67 | 4 | **6.0%** |
| **TOTAL GENERAL / GLOBAL** | **1,765** | **484** | **27.4%** |

> **Nota Metodológica:** Los esquemas DTOs y modelos de datos alcanzan 100% de cobertura. Las líneas no ejecutadas corresponden fundamentalmente a bloques de manejo de errores de red en scrapers externos y ramas condicionales no activadas durante los flujos nominales.

---

## 3. Resultados Detallados de Pruebas

```text
=================================================================
 QA TEST SUITE (7 GRUPOS DE PRUEBA)
=================================================================
[TEST 1] Autenticación Criptográfica & RBAC ..................... [PASS]
[TEST 2] Módulo Cajas/Bancos: CRUD y Soft Delete ................ [PASS]
[TEST 3] Venta Contado e Idempotencia (HTTP 409) ................ [PASS]
[TEST 4] Egresos con Retención SENIAT 14 dígitos ................ [PASS]
[TEST 5] Motor de Backup Determinístico & Restauración .......... [PASS]
[TEST 6] Transferencias Interbancarias .......................... [PASS]
[TEST 7] Tasa Oficial BCV y Política de Fin de Semana ........... [PASS]

=================================================================
 REGRESIÓN FINANCIERA OBLIGATORIA (9 CASOS MATEMÁTICOS)
=================================================================
[CASO 1] Venta de Contado ($100) -> Caja +$100, CxC $0 .......... [PASS]
[CASO 2] Venta Crédito Total ($100) -> Caja $0, CxC $100 ........ [PASS]
[CASO 3] Venta Crédito + Abono ($100/$30) -> Caja +$30, CxC $70 . [PASS]
[CASO 4] Cobro CxC ($30) -> Caja +$30, CxC -$30 ................. [PASS]
[CASO 5] Deuda Histórica ($500) -> Ventas $0, CxC $500 .......... [PASS]
[CASO 6] Cobro Histórico ($200) -> Caja +$200, CxC $300 ......... [PASS]
[CASO 7] Gasto con Retención SENIAT 14 dígitos .................. [PASS]
[CASO 8] Transferencia entre Cuentas Activas .................... [PASS]
[CASO 9] Clean Slate Protegido Multinivel ....................... [PASS]
```
