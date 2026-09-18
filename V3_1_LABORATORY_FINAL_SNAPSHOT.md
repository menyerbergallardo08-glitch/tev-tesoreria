# PROTOCOLO DE SNAPSHOT Y CIERRE DE LABORATORIO (V3.1)
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

---

### 1. Mecanismo de Control de Contaminación
Para garantizar que los datos de prueba generados durante el piloto de 7 días no interfieran con la apertura financiera oficial:

1. **Identificador del Laboratorio**:
   - `LABORATORY_ID`: `TEV-LAB-7DAYS-2026`
   - `LAB_MODE`: `TRUE`
   - `REAL_FINANCIAL_DATA`: `0`
2. **Snapshot de Respaldo Previo al Cierre**:
   - Cada día de piloto culmina con un snapshot determinístico almacenado en `tev-tesoreria-backups-prod` con el prefijo `LAB_`.
3. **Restablecimiento Limpio para Go-Live Real (Clean Slate)**:
   - Al concluir los 7 días de campo y aprobarse el backlog de mejoras, la gobernanza ejecutará la purga controlada (`POST /api/system/clean-slate`) protegida por `MASTER_ADMIN_KEY` para devolver la base a estado virgen antes de la carga de saldos reales de apertura.

---

### 2. Estado Actual de la Base de Producción
- **Transacciones de Venta Reales**: `0`
- **Cobros Reales**: `0`
- **Gastos Reales**: `0`
- **Cuentas por Cobrar Reales**: `0`
- **Cuentas Base de Tesorería**: `10`
- **Estado de Aislamiento**: **100% BLINDADO**
