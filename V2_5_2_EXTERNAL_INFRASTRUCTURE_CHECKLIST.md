# V2.5.2 — EXTERNAL INFRASTRUCTURE READINESS CHECKLIST

**Sistema**: Todo Eléctrico Valencia (TEV) — Sistema de Tesorería y Flujo de Caja  
**Versión**: `2.1.0-Enterprise-Modular`  
**Rol de Emisión**: Senior Software Architect & Lead DevOps / SRE  
**Fecha de Emisión**: 17 de Septiembre de 2026  
**Estado General**: **LOCAL ARCHITECTURE VERIFIED / EXTERNAL CLOUD PROVISIONING PENDING USER CONFIGURATION**

---

## SECCIÓN A: POSTGRESQL STAGING

* **Proveedor**: Supabase (o Render PostgreSQL).
* **Recurso Requerido**: Proyecto / Instancia PostgreSQL dedicada exclusivamente para Staging.
* **Database Requerida**: `postgres` (o nombre de base de datos dedicada, ej. `tev_staging`).
* **Usuario Requerido**: `postgres` (o usuario con privilegios de creación de tablas y secuencias).
* **SSL Requerido**: `require` (habilitado por defecto en conexiones cloud).
* **Variable Requerida**: `DATABASE_URL` (formato estándar `postgresql://<user>:<password>@<host>:5432/<db>?sslmode=require`).
* **Estado Actual**: `PENDING MANUAL PROVIDER PROVISIONING`.
* **Acción Manual Concreta**:
  1. Ingresar a [Supabase Dashboard](https://supabase.com) y crear un nuevo proyecto llamado `tev-tesoreria-staging`.
  2. Ir a **Project Settings** $\rightarrow$ **Database** $\rightarrow$ **Connection string** (URI en modo Session o Transaction Pooler).
  3. Guardar la URI para configurarla en el panel de Render.

---

## SECCIÓN B: REMOTE BACKUP (S3 / CLOUDFLARE R2)

* **Proveedor**: Cloudflare R2 (o Amazon Web Services S3).
* **Bucket Requerido**: `tev-tesoreria-backups-staging`.
* **Endpoint Requerido**: `https://<account_id>.r2.cloudflarestorage.com` (o endpoint S3 regional).
* **Credenciales Requeridas**:
  * `S3_ENDPOINT_URL`
  * `S3_BUCKET`
  * `S3_ACCESS_KEY_ID`
  * `S3_SECRET_ACCESS_KEY`
  * `S3_REGION` (`auto` para R2, o `us-east-1` para S3).
* **Estado Actual**: `PENDING MANUAL PROVIDER PROVISIONING`.
* **Acción Manual Concreta**:
  1. Ingresar a [Cloudflare Dashboard](https://dash.cloudflare.com) $\rightarrow$ **R2 Object Storage**.
  2. Crear un bucket llamado `tev-tesoreria-backups-staging`.
  3. Ir a **Manage R2 API Tokens** $\rightarrow$ **Create API Token** con permisos de lectura y escritura sobre el bucket.
  4. Guardar las claves de acceso para configurarlas en Render.

---

## SECCIÓN C: RENDER STAGING (WEB SERVICE)

* **Repositorio**: `https://github.com/menyerbergallardo08-glitch/tev-tesoreria`
* **Rama (Branch)**: `main`
* **Build Command**: `pip install -r requirements.txt`
* **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
* **Health Check Path**: `/health`
* **Entorno (Environment)**: `Python 3.12.8`
* **Variables de Entorno Requeridas en Render Dashboard**:
  * `ENVIRONMENT` = `staging`
  * `DATABASE_URL` = `<URI_POSTGRESQL_STAGING>`
  * `JWT_SECRET_KEY` = `<CLAVE_SECRETA_JWT_MINIMO_32_CHARS>`
  * `ACCESS_TOKEN_EXPIRE_HOURS` = `12`
  * `MASTER_ADMIN_KEY` = `<CLAVE_MAESTRA_GOBERNANZA_STAGING>`
  * `CORS_ORIGINS` = `https://tev-tesoreria-staging.onrender.com,http://localhost:8000`
  * `S3_ENDPOINT_URL` = `<ENDPOINT_R2_STAGING>`
  * `S3_BUCKET` = `tev-tesoreria-backups-staging`
  * `S3_ACCESS_KEY_ID` = `<R2_ACCESS_KEY_ID>`
  * `S3_SECRET_ACCESS_KEY` = `<R2_SECRET_ACCESS_KEY>`
  * `S3_REGION` = `auto`
* **Estado Actual**: `PENDING MANUAL PROVIDER CONNECTION`.
* **Acción Manual Concreta**:
  1. Ingresar a [Render Dashboard](https://dashboard.render.com).
  2. Hacer clic en **New +** $\rightarrow$ **Web Service** y conectar el repositorio `menyerbergallardo08-glitch/tev-tesoreria`.
  3. En **Environment Variables**, cargar las variables anteriores y desplegar (**Create Web Service**).

---

## SECCIÓN D: VALIDACIÓN OPERACIONAL (SMOKE TEST INMEDIATO POST-DESPLIEGUE)

Una vez completados los 3 pasos anteriores, se deben ejecutar inmediatamente estas 12 validaciones:

1. **Health Check Público**: `curl -s https://tev-tesoreria-staging.onrender.com/health` $\rightarrow$ `200 OK` (`status: healthy`).
2. **Database Health Check**: `curl -s https://tev-tesoreria-staging.onrender.com/api/system/health` $\rightarrow$ `200 OK` (`database: OK`).
3. **Chequeo SQL `SELECT 1`**: Confirmado automáticamente por el endpoint de salud interno.
4. **Schema / Migraciones**: Verificación de las 11 tablas creadas por SQLAlchemy `Base.metadata.create_all` e inicializadas por `init_db.py`.
5. **Smoke Test de Autenticación y RBAC**: Login con usuario administrador y obtención de token JWT.
6. **Backup Remoto Real**: Ejecución de `POST /api/system/backup` desde la UI/API verificando subida a Cloudflare R2 con `remote_status: REMOTE_BACKUP_SUCCESS`.
7. **Descarga del Backup**: Confirmación de la existencia del objeto `.json` en el bucket R2.
8. **Restore en DB Independiente**: Restauración del payload JSON y validación de `RESTORE_SUCCESS`.
9. **Verificación de Checksum SHA-256**: Comprobación de coincidencia del hash del archivo descargado con el registrado en `audit_logs`.
10. **Inserción de Prueba Post-Restore**: Registro de una venta o movimiento para certificar que las secuencias de PostgreSQL no colisionan.
11. **QA Suite**: Validación de no regresión en endpoints (`7/7 PASS`).
12. **Financial Regression**: Confirmación de integridad matemática al centavo (`9/9 PASS`).
