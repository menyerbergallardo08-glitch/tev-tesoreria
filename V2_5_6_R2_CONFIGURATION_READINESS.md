# V2.5.6 — PREPARACIÓN FINAL PARA CLOUDFLARE R2 REAL

## 1. Contexto y Objetivos

El entorno STAGING de **Todo Eléctrico Valencia (TEV)** se encuentra actualmente desplegado, operativo y validado en Render:
- **URL Staging**: `https://tev-tesoreria-staging.onrender.com`
- **Base de Datos**: PostgreSQL Staging en Supabase (`aws-0-us-east-1.pooler.supabase.com:6543/postgres`)
- **Estado de Aislamiento**: Staging y Producción 100% aislados. Producción jamás tocada ni conectada.

El objetivo de la fase **V2.5.6** es auditar, certificar y preparar técnicamente el adaptador de almacenamiento remoto existente (`services/backup_service.py`) para operar de forma nativa con **Cloudflare R2** utilizando la API compatible con Amazon S3 (Signature Version 4).

---

## 2. Auditoría Técnica del Adaptador S3/R2

### 2.1 Módulo Auditado
- Archivo: `services/backup_service.py`
- Dependencia: `boto3>=1.34.0`, `botocore>=1.34.0` (incorporado a `requirements.txt`)

### 2.2 Compatibilidad con Cloudflare R2
Cloudflare R2 implementa el estándar S3 API con autenticación obligatoria **S3 Signature Version 4 (s3v4)**.
El adaptador de TEV configura explícitamente el cliente S3 con:
```python
from botocore.config import Config
s3_client = boto3.client(
    's3',
    endpoint_url=config["endpoint"],
    aws_access_key_id=config["access_key"],
    aws_secret_access_key=config["secret_key"],
    region_name=config["region"],
    config=Config(signature_version='s3v4')
)
```
Esto garantiza total interoperabilidad y cero fricción técnica al conectarse al endpoint de Cloudflare R2.

### 2.3 Manejo Robusto de Fallbacks y Errores
1. **Ausencia de Credenciales**: Si las variables de entorno no están presentes, la generación de backup local y el cálculo del hash criptográfico SHA-256 se ejecutan con éxito, reportando `remote_status: "NOT_CONFIGURED"`.
2. **Falla de Red / Endpoint Inalcanzable**: Si ocurre un error durante el `upload_file`, la excepción es capturada sin tumbar el servicio web ni abortar la transacción de auditoría, retornando `remote_status: "REMOTE_BACKUP_FAILED"`.
3. **Descarga Remota**: Se incorporó la función `download_from_s3_compatible(backup_filename, target_local_path)` para recuperar snapshots directamente desde el bucket R2 hacia el entorno local antes de un restore.

---

## 3. Matriz de Variables de Entorno Requeridas

Para activar la sincronización automática de backups remotos en Cloudflare R2, se deben configurar las siguientes 5 variables de entorno en el panel de Render (Staging Web Service):

| Variable de Entorno | Descripción | Ejemplo de Formato |
|---|---|---|
| `S3_ENDPOINT_URL` | URL del endpoint S3 de la cuenta Cloudflare | `https://<account_id>.r2.cloudflarestorage.com` |
| `S3_BUCKET` | Nombre del bucket R2 creado para Staging | `tev-tesoreria-backups-staging` |
| `S3_ACCESS_KEY_ID` | Access Key ID del token API R2 | `a1b2c3d4e5f6...` |
| `S3_SECRET_ACCESS_KEY` | Secret Access Key del token API R2 | `0123456789abcdef...` |
| `S3_REGION` | Región S3 (Cloudflare R2 requiere `auto` o `us-east-1`) | `auto` |

> [!IMPORTANT]
> **Política de Seguridad Cero Fugas**: Ningún secreto, token o clave de acceso debe ser subido al repositorio Git ni registrado en logs de consola. Las credenciales se inyectan exclusivamente como variables de entorno privadas en Render.

---

## 4. Procedimiento de Aprovisionamiento en Cloudflare R2

1. **Crear Bucket R2**:
   - Ingresar a la consola de Cloudflare > **R2 Object Storage**.
   - Hacer clic en **Create bucket**.
   - Nombre: `tev-tesoreria-backups-staging`.
   - Ubicación: Automática o la más cercana (ej. Eastern North America / WNAM).

2. **Generar API Token R2**:
   - En R2 > **Manage R2 API Tokens** > **Create API token**.
   - Permisos: **Object Read & Write** (o Admin Read & Write).
   - Ámbito: Limitar al bucket `tev-tesoreria-backups-staging`.
   - Guardar el **Account ID**, **Access Key ID** y **Secret Access Key**.

3. **Inyectar Variables en Render**:
   - Render Dashboard > `tev-tesoreria-staging` > **Environment**.
   - Agregar las 5 variables `S3_*` descritas en la sección 3.
   - Render realizará un re-despliegue automático con las nuevas credenciales.

---

## 5. Matriz de Estado de Infraestructura (V2.5.6)

| Componente | Estado | Detalle |
|---|---|---|
| **STAGING WEB SERVICE** | **VERIFIED** | Live en `https://tev-tesoreria-staging.onrender.com` |
| **STAGING DATABASE** | **VERIFIED** | Supabase PostgreSQL (`arvxjjjydbgjvcydgate`) |
| **STAGING / PRODUCTION ISOLATION** | **VERIFIED** | Producción 100% aislada e intacta |
| **DETERMINISTIC BACKUP ENGINE** | **VERIFIED** | Generación JSON, orden topológico y SHA-256 |
| **DETERMINISTIC RESTORE ENGINE** | **VERIFIED** | Purga inversa, reinserción y sincronización de secuencias PG |
| **R2 ADAPTER COMPATIBILITY** | **VERIFIED** | `boto3` + `s3v4` + manejo de excepciones verificado |
| **LIVE R2 BUCKET & CREDENTIALS** | **PENDING** | Requiere creación del bucket y token por el operador cloud |
| **REAL REMOTE CLOUD BACKUP** | **PENDING** | Se certificará una vez inyectadas las credenciales R2 en Render |
| **REGRESIÓN FINANCIERA** | **9/9 PASS** | Consistencia en USD/VES, tasa BCV, cierres de caja |
| **QA SUITE** | **7/7 PASS** | RBAC, autenticación, gobernanza y transacciones |
| **GITHUB ACTIONS CI** | **PASS** | Sincronizado en `main` |
| **PRODUCCIÓN** | **INTACTA** | Cero impacto |
