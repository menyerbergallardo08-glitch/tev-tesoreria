# RUNBOOK DE ROLLBACK Y CONTINGENCIA EN PRODUCCIÓN
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

---

## 1. Detección y Clasificación del Incidente
- **Criterios de Activación de Rollback**:
  - Falta de disponibilidad del backend (`5xx` continuos en `/health`).
  - Imposibilidad de autenticación o degradación en base de datos.
  - Inconsistencia crítica detectada en balances de cuentas o registro de ventas.
  - Corrupción de datos o fallo en el pooler de PostgreSQL.

---

## 2. Protocolo de Ejecución de Rollback Paso a Paso

### Paso 1: Contención y Detención Inmediata
- Suspender tráfico en el balanceador o poner la aplicación en modo de mantenimiento temporal para evitar escrituras financieras divergentes.

### Paso 2: Preservación de Evidencia y Logs
- Descargar logs del servicio web de Render y del servidor de base de datos.
- Registrar el último ID de transacción procesado con éxito.

### Paso 3: Reversión del Código / Despliegue
- Si el fallo es de aplicación/código:
  - En Render Dashboard > `Deployments` > Seleccionar el commit estable previo (ej. `f38cc0d`) > Clic en **Rollback to this deploy**.
  - O vía Git: hacer revert del commit fallido y hacer `push origin main`.

### Paso 4: Reversión de Base de Datos (Disaster Recovery)
- Si el fallo involucró corrupción de datos en la base de datos productiva:
  1. Descargar el último backup determinístico verificado desde Cloudflare R2 (o almacenamiento S3 productivo).
  2. Verificar integridad del archivo calculando su hash SHA-256 local y comparándolo con el registro de auditoría.
  3. Ejecutar el script de restauración determinística en estricto orden inverso topológico (purgado seguro) y orden topológico directo (reinserción y reajuste de secuencias PostgreSQL).

### Paso 5: Validación y Smoke Test
- Ejecutar el conjunto de pruebas no destructivas [`PRODUCTION_SMOKE_TEST.md`](file:///C:/Users/GATEWAY/Desktop/CLIENTES%20DE%20CONSULTORIA/TODO%20ELECTRICO%20VALENCIA/SISTEMA%20DE%20TESORERIA%20Y%20FLUJO%20DE%20CAJA/PRODUCTION_SMOKE_TEST.md).
- Verificar que `GET /health` devuelva `200 OK` y que la conexión a la base de datos reporte `status: healthy`.

### Paso 6: Reanudación Operativa
- Notificar a la Gerencia General y Administradora para reabrir el acceso a cajas y reanudar las operaciones cotidianas.
