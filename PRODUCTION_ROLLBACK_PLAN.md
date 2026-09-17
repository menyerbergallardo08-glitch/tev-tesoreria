# PLAN DE ROLLBACK Y RECUPERACIÓN ANTE DESASTRES (PRODUCTION ROLLBACK PLAN)
## Todo Eléctrico Valencia (TEV) — Sistema de Tesorería y Flujo de Caja
**Versión de Referencia:** `2.1.0-Enterprise-Modular`  
**Objetivo:** Procedimiento operativo estándar (SOP) para revertir de manera inmediata y segura cualquier anomalía o fallo crítico detectado durante o después de un despliegue en producción.

---

## 1. Criterios de Activación de Rollback (Triggers)

El procedimiento de rollback debe activarse de inmediato si se presenta cualquiera de las siguientes condiciones en los primeros 30 minutos post-despliegue:
* **Fallo Crítico de Disponibilidad:** Errores HTTP 500 sostenidos (> 1%) o indisponibilidad total del servicio en Render.
* **Descuadre Financiero:** Cualquier inconsistencia en el registro de ventas, cálculo de abonos a crédito o alteración no controlada de saldos de caja/bancos.
* **Fallo Criptográfico / RBAC:** Imposibilidad de iniciar sesión para los usuarios autorizados (`cajera`, `administradora`, `directivo`) o filtración de permisos.
* **Corrupción de Esquema de Base de Datos:** Errores de sintaxis SQL o fallos en llaves foráneas/secuencias en Supabase PostgreSQL.

---

## 2. Procedimiento de Rollback en 9 Pasos

```text
=============================================================================
                    PROTOCOLO DE ROLLBACK PRODUCTIVO
=============================================================================
  [PASO 1] Identificar Release y Congelar Tráfico
  [PASO 2] Diagnóstico Rápido y Decisión Go/Rollback
  [PASO 3] Detener Promoción y Despliegue en Render
  [PASO 4] Revertir Commit en Rama 'main' de GitHub
  [PASO 5] Restaurar Snapshot / Backup de Base de Datos
  [PASO 6] Forzar Re-despliegue de Versión Estable Anterior
  [PASO 7] Invalidar Sesiones y Tokens JWT Activos
  [PASO 8] Ejecutar Smoke Test de Sanidad Financiera
  [PASO 9] Notificación a Gerencia y Registro de Incidente
=============================================================================
```

### Paso 1: Identificar Release y Congelar Tráfico
* Identificar el ID del commit fallido y notificar al equipo que el sistema entra en ventana de contingencia operativa.

### Paso 2: Diagnóstico Rápido (Máximo 5 minutos)
* Revisar los logs en tiempo real en Render (`render.com/dashboard`) para determinar si el fallo es de variables de entorno, código o base de datos. Si no tiene solución inmediata en < 3 minutos, proceder al rollback inmediato.

### Paso 3: Detener Promoción y Despliegue en Render
* Cancelar cualquier compilación o despliegue en curso desde el dashboard de Render.

### Paso 4: Revertir Commit en Git
* En el repositorio local / GitHub:
  ```bash
  # Revertir al último commit certificado estable
  git revert HEAD --no-edit
  git push origin main
  ```
  *(O sincronizar los archivos estables certificados previos mediante `sync_github.py`).*

### Paso 5: Restaurar Base de Datos (Si hubo alteración de esquema o datos)
* Si el despliegue ejecutó cambios de datos inconsistentes:
  1. Conectar a la base de datos de producción mediante sesión administrativa autorizada.
  2. Ejecutar la restauración del último snapshot/backup estructurado `TEV_BACKUP_*.json` generado previo al despliegue.
  3. Reajustar secuencias PostgreSQL:
     ```sql
     SELECT setval(pg_get_serial_sequence('transactions', 'id'), coalesce(max(id), 1)) FROM transactions;
     ```

### Paso 6: Forzar Re-despliegue en Render
* Disparar manualmente el botón **"Clear build cache & deploy"** en Render para asegurar que la versión previa estable quede 100% activa.

### Paso 7: Revocación de Sesiones JWT
* En caso de compromiso de seguridad, rotar la variable de entorno `JWT_SECRET_KEY` en Render. Esto cerrará automáticamente todas las sesiones activas forzando re-login limpio.

### Paso 8: Smoke Test de Sanidad Financiera
* Ejecutar la verificación básica en vivo:
  1. Login de Cajera, Administradora y Directivo.
  2. Consulta de saldos de cuentas en `/api/accounts`.
  3. Comprobación del último cierre de caja y correlativos de notas/facturas.

### Paso 9: Notificación y Cierre de Incidente
* Notificar a la Dirección General de TEV que el sistema ha sido restablecido a su estado nominal y documentar el informe post-mortem del incidente.

---

## 3. Matriz de Responsabilidades

| Rol | Responsabilidad en Rollback |
| :--- | :--- |
| **Release Manager / Lead Engineer** | Autorizar y ejecutar la reversión de Git y Render. |
| **Database Administrator** | Verificar la integridad y secuencias en Supabase PostgreSQL. |
| **QA Lead** | Ejecutar el Smoke Test de sanidad post-rollback. |
| **Dirección General TEV** | Recibir informe ejecutivo y autorizar reapertura de operaciones. |
