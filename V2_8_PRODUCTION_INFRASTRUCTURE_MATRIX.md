# MATRIZ DE INFRAESTRUCTURA Y AISLAMIENTO DE PRODUCCIÓN (V2.8)
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

---

## 1. Matriz de Aislamiento de Recursos: Staging vs Producción

| Recurso / Componente | Entorno STAGING | Entorno PRODUCCIÓN | Estado de Aislamiento | Validación Técnica |
|---|---|---|---|---|
| **Base de Datos** | Supabase PostgreSQL (`arvxjj...`) | Supabase PostgreSQL (`tev-tesoreria-prod`) | **100% Independiente** | `STAGING_DB != PROD_DB` |
| **Almacenamiento R2** | `tev-tesoreria-backups-staging` | `tev-tesoreria-backups-prod` | **100% Independiente** | `STAGING_BUCKET != PROD_BUCKET` |
| **Token API S3/R2** | Token R2 Staging | Token R2 Producción (Dedidaco) | **100% Independiente** | Credenciales no compartidas |
| **JWT Secret Key** | Clave Privada Staging (Render Env) | Clave Privada Prod (32+ caracteres) | **100% Independiente** | `JWT_SECRET_STAGING != JWT_SECRET_PROD` |
| **Master Admin Key** | Clave Maestra Staging (Render Env) | Clave Maestra Prod (32+ caracteres) | **100% Independiente** | `MASTER_KEY_STAGING != MASTER_KEY_PROD` |
| **Servicio Web** | Render `tev-tesoreria-staging` | Render `tev-tesoreria-prod` | **100% Independiente** | Instancias separadas |
| **Entorno (`ENVIRONMENT`)** | `staging` | `production` | **100% Independiente** | Cierre de docs en Prod |
| **Superficie OpenAPI** | Swagger / OpenAPI (/docs) | Desactivada (`None`) | **Protegida en Prod** | Verificado en `main.py` |
| **Políticas CORS** | `https://tev-tesoreria-staging.onrender.com` | Dominio Web Oficial de Producción | **Restringido a Prod** | Sin localhost en Prod |
| **Datos Financieros** | Sandbox / Pruebas Verificadas | Base Limpia (0 Transacciones) | **100% Desacoplado** | Cero migración de ventas |

---

## 2. Inventario de Variables de Entorno para Render Producción

| Variable de Entorno | Valor / Requisito | Propósito de Seguridad |
|---|---|---|
| `ENVIRONMENT` | `production` | Desactiva OpenAPI/Swagger y activa headers productivos |
| `DATABASE_URL` | URI Session Pooler de Supabase Prod | Conexión SSL obligatoria a la base dedicada |
| `JWT_SECRET_KEY` | Cadena aleatoria de 32+ caracteres | Cifra y firma tokens JWT de usuarios reales |
| `MASTER_ADMIN_KEY` | Cadena aleatoria de 32+ caracteres | Protege funciones críticas de gobernanza (Clean Slate, Restore) |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `12` | Expiración forzada de sesiones operativas |
| `CORS_ORIGINS` | Dominio corporativo final | Evita solicitudes cruzadas no autorizadas |
| `S3_ENDPOINT_URL` | URL de cuenta Cloudflare R2 | Endpoint compatible con S3v4 |
| `S3_BUCKET` | `tev-tesoreria-backups-prod` | Bucket aislado para snapshots productivos |
| `S3_ACCESS_KEY_ID` | Access Key ID del Token R2 Prod | Acceso de solo lectura/escritura al bucket prod |
| `S3_SECRET_ACCESS_KEY` | Secret Key del Token R2 Prod | Credencial criptográfica de almacenamiento |
| `S3_REGION` | `auto` | Región estándar S3 compatible para Cloudflare R2 |

> [!IMPORTANT]
> **Política de Seguridad Cero Fugas**: Ningún secreto, token o clave de acceso debe ser subido al repositorio Git ni registrado en logs de consola. Las credenciales se inyectan exclusivamente como variables de entorno privadas en Render.
