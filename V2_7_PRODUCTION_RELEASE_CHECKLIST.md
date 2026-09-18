# CHECKLIST DE ACTIVACIÓN PRODUCTIVA (V2.7)
## Todo Eléctrico Valencia — Sistema de Tesorería y Flujo de Caja

---

## 1. Código y Calidad Técnica
- [x] Código congelado en Release Candidate (`V2.7-RELEASE-CANDIDATE`).
- [x] Commit SHA identificado y verificado (`f38cc0d`).
- [x] Integración Continua (CI) en GitHub Actions en estado `SUCCESS`.
- [x] QA Test Suite ejecutada y aprobada (`7/7 PASS`).
- [x] Regresión Financiera Obligatoria ejecutada y aprobada (`9/9 PASS`).
- [x] Production Readiness Gate (V2.6) ejecutado y aprobado (`12/12 PASS`).
- [x] Auditoría de Secretos aprobada (Cero credenciales en Git).
- [x] Staging Live verificado y operativo (`https://tev-tesoreria-staging.onrender.com`).
- [x] Disaster Recovery real certificado con Cloudflare R2 (`V2.5.8 CERTIFIED`).

---

## 2. Infraestructura y Aislamiento de Producción
- [ ] Base de datos PostgreSQL independiente para Producción (Supabase Dedicated / AWS RDS).
- [ ] Cadena de conexión `DATABASE_URL` productiva generada y aislada de Staging.
- [ ] Clave criptográfica `JWT_SECRET_KEY` productiva de 32+ caracteres generada.
- [ ] Clave de gobernanza `MASTER_ADMIN_KEY` productiva generada.
- [ ] Bucket de almacenamiento remoto Cloudflare R2 / S3 independiente (`tev-tesoreria-backups-prod`).
- [ ] Credenciales de acceso S3/R2 productivas generadas (`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`).
- [ ] Dominio web de producción configurado con certificado SSL/TLS (HTTPS obligatorio).
- [ ] Política CORS restringida al dominio productivo (`CORS_ORIGINS`).
- [ ] Documentación OpenAPI (`/docs`, `/redoc`, `/openapi.json`) desactivada con `ENVIRONMENT=production`.

---

## 3. Gobernanza y Operación
- [x] Runbook de inicialización de base de datos documentado ([`PRODUCTION_DATABASE_INITIALIZATION.md`](file:///C:/Users/GATEWAY/Desktop/CLIENTES%20DE%20CONSULTORIA/TODO%20ELECTRICO%20VALENCIA/SISTEMA%20DE%20TESORERIA%20Y%20FLUJO%20DE%20CAJA/PRODUCTION_DATABASE_INITIALIZATION.md)).
- [x] Runbook de rollback operacional documentado ([`PRODUCTION_ROLLBACK_RUNBOOK.md`](file:///C:/Users/GATEWAY/Desktop/CLIENTES%20DE%20CONSULTORIA/TODO%20ELECTRICO%20VALENCIA/SISTEMA%20DE%20TESORERIA%20Y%20FLUJO%20DE%20CAJA/PRODUCTION_ROLLBACK_RUNBOOK.md)).
- [x] Protocolo de smoke test no destructivo preparado ([`PRODUCTION_SMOKE_TEST.md`](file:///C:/Users/GATEWAY/Desktop/CLIENTES%20DE%20CONSULTORIA/TODO%20ELECTRICO%20VALENCIA/SISTEMA%20DE%20TESORERIA%20Y%20FLUJO%20DE%20CAJA/PRODUCTION_SMOKE_TEST.md)).
- [ ] Creación de usuario administrador inicial productivo completada mediante script seguro.
- [ ] Responsable operativo de turno y equipo directivo notificados.
