# V2.8.1 — CIERRE Y ESPECIFICACIÓN DE INFRAESTRUCTURA DE PRODUCCIÓN
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

**Fecha**: 18 de Septiembre de 2026  
**Entorno STAGING**: LIVE y Operativo (`https://tev-tesoreria-staging.onrender.com`)  
**Base de Datos STAGING**: Supabase PostgreSQL (`arvxjjjydbgjvcydgate`)  
**Almacenamiento STAGING**: Cloudflare R2 (`tev-tesoreria-backups-staging`)  
**Estado de Producción**: `PRODUCTION_OPERATIONAL = FALSE`  
**Salvaguarda Financiera**: **STAGING NO TOCADO / PRODUCCIÓN NO TOCADA / CERO OPERACIONES FINANCIERAS EJECUTADAS**  

---

## 1. Identificación y Estado Real de Recursos de Producción

| Recurso | Proveedor / Tecnología | Estado Actual | Acción Externa / Paso de Provisionamiento |
|---|---|---|---|
| **PostgreSQL Producción** | Supabase Dedicated | `PENDING_EXTERNAL_PROVISIONING` | Crear proyecto `tev-tesoreria-prod` en Supabase y obtener URL IPv4 Pooler |
| **Storage de Backups** | Cloudflare R2 | `PENDING_EXTERNAL_PROVISIONING` | Crear bucket `tev-tesoreria-backups-prod` y generar API Token dedicado |
| **Web Service Producción** | Render Web Service | `PENDING_EXTERNAL_PROVISIONING` | Crear Web Service `tev-tesoreria-prod` desde GitHub `main` |
| **Secretos Criptográficos** | Render Environment | `PENDING_EXTERNAL_PROVISIONING` | Inyectar `JWT_SECRET_KEY` y `MASTER_ADMIN_KEY` independientes de 32+ chars |
| **Dominio Corporativo** | DNS / HTTPS | `PENDING` | Asignar dominio oficial y configurar registros CNAME/A hacia Render |
| **Superficie OpenAPI** | FastAPI (`main.py`) | `READY` | Desactivada automáticamente (`None`) en `ENVIRONMENT=production` |
| **Políticas CORS** | `CORS_ORIGINS` | `READY` | Restringido exclusivamente al dominio productivo |
| **Protocolo HTTPS** | SSL/TLS Automático | `READY` | Gestionado por Render / Cloudflare |
| **Monitoreo & Logs** | Render Logs + Supabase | `READY` | Pistas de auditoría inmutables en base de datos |

---

## 2. Matriz de Aislamiento Certificada

| RECURSO | STAGING | PRODUCCIÓN | AISLAMIENTO | ESTADO | EVIDENCIA |
|---|---|---|---|---|---|
| **PostgreSQL** | `arvxjjjydbgjvcydgate` | `tev-tesoreria-prod` | **100% Independiente** | `PENDING_EXTERNAL_PROVISIONING` | Host y pooler separados |
| **Bucket R2** | `tev-tesoreria-backups-staging` | `tev-tesoreria-backups-prod` | **100% Independiente** | `PENDING_EXTERNAL_PROVISIONING` | Buckets y tokens dedicados |
| **JWT Secret** | Privado en Render Staging | Privado en Render Prod | **100% Independiente** | `PENDING_EXTERNAL_PROVISIONING` | Claves criptográficas distintas |
| **Master Admin Key** | Privada en Render Staging | Privada en Render Prod | **100% Independiente** | `PENDING_EXTERNAL_PROVISIONING` | Claves de gobernanza distintas |
| **Web Service** | `tev-tesoreria-staging` | `tev-tesoreria-prod` | **100% Independiente** | `PENDING_EXTERNAL_PROVISIONING` | Servicios web desacoplados |
| **Environment** | `staging` | `production` | **100% Independiente** | `READY` | Configurado en `render.yaml` |
| **CORS Origins** | Subdominio Staging | Dominio Corporativo | **100% Independiente** | `READY` | Aislamiento de orígenes |
| **Documentación API** | Desactivada | Desactivada | **Protegida** | `READY` | OpenAPI `None` en producción |
| **Production Health** | Staging (200 OK) | Por desplegar | **Desacoplado** | `PENDING` | Sin tráfico productivo |
| **Production DB Health**| Staging DB (200 OK) | Por desplegar | **Desacoplado** | `PENDING` | Sin conexión a BD prod |

---

## 3. Procedimiento Operativo para Aprovisionamiento Externo

### 3.1 Base de Datos en Supabase
1. Ingresar a [https://supabase.com/dashboard](https://supabase.com/dashboard) > **New Project**.
2. Nombre: `tev-tesoreria-prod`.
3. Contraseña de BD: Generar una clave segura de 32+ caracteres.
4. Región: `us-east-1` (misma región que Staging para baja latencia con Render).
5. Copiar la URI de conexión del **Session Pooler (IPv4)**:
   `postgresql://postgres.<ref>:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require`

### 3.2 Almacenamiento en Cloudflare R2
1. Ingresar a [https://dash.cloudflare.com/?to=/:account/r2/overview](https://dash.cloudflare.com/?to=/:account/r2/overview) > **Create bucket**.
2. Nombre del Bucket: `tev-tesoreria-backups-prod`.
3. Ir a **Manage R2 API Tokens** > **Create API token**:
   - Nombre: `tev-prod-backup-token`
   - Permisos: **Object Read & Write**
   - Ámbito: Limitar a `tev-tesoreria-backups-prod`.
4. Copiar: `Account ID` (para el endpoint), `Access Key ID` y `Secret Access Key`.

### 3.3 Servicio Web en Render
1. Ingresar a [https://dashboard.render.com](https://dashboard.render.com) > **New** > **Web Service**.
2. Conectar repositorio: `menyerbergallardo08-glitch/tev-tesoreria` (Branch `main`).
3. Nombre: `tev-tesoreria-prod`.
4. Runtime: `Python`.
5. Build Command: `pip install -r requirements.txt`.
6. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
7. En la pestaña **Environment**, inyectar las 11 variables de producción requeridas.

---

## 4. Pruebas de Regresión y Calidad Técnica

- **Compileall**: **PASS**
- **QA Test Suite (TEV v2.1)**: **7/7 PASS**
- **Regresión Financiera Obligatoria**: **9/9 PASS**
- **Production Readiness Gate Suite**: **12/12 PASS**
- **GitHub Actions CI**: **SUCCESS**

---

## 5. Dictamen Técnico

# **INFRASTRUCTURE PARTIALLY READY — PENDING EXTERNAL PROVISIONING**

**Nota de Seguridad**:  
La producción **NO se encuentra operacional** (`PRODUCTION_OPERATIONAL = FALSE`). No se ha creado ningún usuario final, no se han migrado transacciones y no se han ejecutado operaciones financieras sobre producción. La activación formal se ejecutará exclusivamente en la fase **V2.9 CONTROLLED PRODUCTION ACTIVATION**.
