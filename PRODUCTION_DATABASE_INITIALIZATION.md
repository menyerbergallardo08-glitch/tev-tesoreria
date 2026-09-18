# PROTOCOLO DE INICIALIZACIÓN DE BASE DE DATOS EN PRODUCCIÓN
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

> [!CAUTION]
> **REGLA DE AISLAMIENTO ABSOLUTO**: Este procedimiento solo debe ejecutarse cuando la base de datos de producción haya sido aprovisionada de forma independiente y aislada de Staging y Desarrollo. Jamás reutilizar credenciales de Staging.

---

## 1. Preparación Previa
1. **Verificar Instancia PostgreSQL Independiente**:
   - Proveedor recomendado: Supabase Dedicated PostgreSQL (o AWS RDS / Render Managed PostgreSQL).
   - Versión: PostgreSQL 15+.
   - Conexión con pooling seguro IPv4 (Session Pooler / PgBouncer).
2. **Generar Credenciales Fuertes**:
   - Generar password aleatorio de 32+ caracteres.
   - Restringir acceso por IP / SSL obligatorio (`sslmode=require`).
3. **Backup Inicial**:
   - Si la base de datos tiene datos previos, tomar snapshot manual antes de cualquier alteración.

---

## 2. Inicialización de Esquema y Migraciones
El sistema utiliza SQLAlchemy ORM con inicializador determinístico topológico (`init_db.py` / `database.py`):

1. **Orden de Creación de Tablas**:
   - `branches` (Padre de estructura)
   - `cash_registers` (Dependiente de sucursal)
   - `users` (Dependiente de sucursal)
   - `budget_categories` (Catálogo maestro)
   - `treasury_accounts` (Cajas y bancos)
   - `account_monthly_balances` (Saldos mensuales)
   - `suppliers` (Proveedores y RIF)
   - `system_settings` (Parámetros y BCV)
   - `transactions` (Movimientos financieros con locking pesimista)
   - `daily_cash_closes` (Arqueos diarios)
   - `audit_logs` (Pistas de auditoría inmutables)

2. **Ejecución del Inicializador**:
   Al levantar la aplicación con `DATABASE_URL` productiva, `init_all()` ejecuta automáticamente:
   - `Base.metadata.create_all(bind=engine)`
   - `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...`
   - Sincronización de catálogos base indispensables (Sucursal Principal `TEV-CENTRO`, Caja `CAJA-01`, Cuentas de Tesorería oficiales).

---

## 3. Catálogos Iniciales vs Datos Financieros
En Producción se inicializan **únicamente** catálogos maestros:
- **Cuentas Bancarias y Cajas Oficiales**: Efectivo USD, Efectivo VES, Bancaribe, Banesco, Banco de Venezuela, BNC, Cashea, Banesco Panamá, Zelle, Binance USDT (todos con saldo inicial $0.00).
- **Categorías Presupuestarias**: `CAT-01` a `CAT-06`.
- **Datos Transaccionales**: Las tablas `transactions`, `daily_cash_closes`, y `account_monthly_balances` inician estrictamente con **0 registros**.

---

## 4. Validación Post-Inicialización (Smoke Test de Esquema)
Ejecutar consulta de conteo para validar el estado limpio:
```sql
SELECT 'branches' as tabla, count(*) FROM branches
UNION ALL
SELECT 'treasury_accounts', count(*) FROM treasury_accounts
UNION ALL
SELECT 'transactions', count(*) FROM transactions
UNION ALL
SELECT 'daily_cash_closes', count(*) FROM daily_cash_closes;
```
*Resultado Esperado: Catálogos cargados, transacciones = 0.*

---

## 5. Procedimiento de Rollback en Base de Datos
Si ocurre una anomalía durante la inicialización:
1. Purgar conexiones activas en el pooler.
2. Si la base era nueva: eliminar esquema público (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`).
3. Si existía snapshot previo: restaurar desde el snapshot determinístico mediante `services.backup_service.restore_deterministic_backup`.
