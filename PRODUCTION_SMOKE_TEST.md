# GUÍA DE SMOKE TEST NO DESTRUCTIVO EN PRODUCCIÓN
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

> [!IMPORTANT]
> **REGLA DE NO ALTERACIÓN PRODUCTIVA**: Este smoke test está compuesto **exclusivamente por lecturas y verificaciones de estado**. Bajo ninguna circunstancia se deben insertar ventas ficticias, egresos de prueba ni transferencias sobre la base productiva.

---

## 1. Verificación de Disponibilidad y Estado del Servicio

1. **Health Check General**:
   - `GET /health`
   - Resultado Esperado: `HTTP 200 OK`
   - Respuesta: `{"status": "healthy", "application": "OK", "version": "2.0.0"}`

2. **Health Check de Base de Datos**:
   - `GET /api/system/health`
   - Resultado Esperado: `HTTP 200 OK`
   - Respuesta: `{"status": "healthy", "application": "OK", "database": "OK", "version": "2.1.0"}`

3. **Cierre de Superficie de Ataque (Swagger / OpenAPI)**:
   - `GET /docs` ➔ Resultado Esperado: `HTTP 404 Not Found`
   - `GET /redoc` ➔ Resultado Esperado: `HTTP 404 Not Found`
   - `GET /openapi.json` ➔ Resultado Esperado: `HTTP 404 Not Found`

---

## 2. Verificación de Autenticación y Autorización

1. **Login de Usuario Autorizado**:
   - `POST /api/auth/login` con credenciales de directivo o administradora.
   - Resultado Esperado: `HTTP 200 OK`, retorno de `access_token` JWT y perfil de usuario.

2. **Consulta de Perfil (`/api/auth/me`)**:
   - `GET /api/auth/me` con cabecera `Authorization: Bearer <token>`.
   - Resultado Esperado: `HTTP 200 OK`, coincidencia de nombre, rol y sucursal.

---

## 3. Verificación de Catálogos y Estado Inicial

1. **Consulta de Cajas y Bancos (`/api/accounts`)**:
   - `GET /api/accounts`
   - Resultado Esperado: `HTTP 200 OK`, listado de las 10 cuentas de tesorería activas con saldo inicial en cero o de balance de apertura.

2. **Consulta de Tasa BCV (`/api/system/bcv-rate`)**:
   - `GET /api/system/bcv-rate`
   - Resultado Esperado: `HTTP 200 OK`, tasa oficial resuelta correctamente.

3. **Consulta de Categorías Presupuestarias (`/api/categories`)**:
   - `GET /api/categories`
   - Resultado Esperado: `HTTP 200 OK`, listado de categorías activas (`CAT-01` a `CAT-06`).

4. **Consulta de Cartera CxC Vacía (`/api/cxc/debts`)**:
   - `GET /api/cxc/debts`
   - Resultado Esperado: `HTTP 200 OK`, retorno de lista limpia `[]` (o con deudas iniciales auditadas).

5. **Consulta de Pistas de Auditoría (`/api/audit/logs`)**:
   - `GET /api/audit/logs`
   - Resultado Esperado: `HTTP 200 OK`, confirmación del evento de inicio de sesión registrado.
