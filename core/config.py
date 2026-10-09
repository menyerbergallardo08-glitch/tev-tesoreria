import os
from typing import List

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development').lower()
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_STAGING = ENVIRONMENT == 'staging'

# Parámetros Institucionales (White-Label / Multi-Empresa)
COMPANY_NAME = os.environ.get('COMPANY_NAME', 'Todo Eléctrico Valencia, C.A.')
COMPANY_RIF = os.environ.get('COMPANY_RIF', 'J-30798687-3')
COMPANY_SLOGAN = os.environ.get('COMPANY_SLOGAN', 'Sistema de Tesorería, Gastos y Flujo de Caja')
PRIMARY_CURRENCY = os.environ.get('PRIMARY_CURRENCY', 'USD')
SECONDARY_CURRENCY = os.environ.get('SECONDARY_CURRENCY', 'VES')

# Parámetros de Seguridad y Sesión
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'todo-electrico-valencia-seguridad-jwt-2026-secret')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get('ACCESS_TOKEN_EXPIRE_HOURS', '12'))
MASTER_ADMIN_KEY = os.environ.get('MASTER_ADMIN_KEY', 'TEV-MASTER-RESET-2026')

# Política FIFO de Respaldo Automático
FIFO_BACKUP_MAX_COUNT = int(os.environ.get('FIFO_BACKUP_MAX_COUNT', '14'))
FIFO_BACKUP_RETENTION_DAYS = int(os.environ.get('FIFO_BACKUP_RETENTION_DAYS', '15'))

def get_cors_origins() -> List[str]:
    if IS_PRODUCTION:
        origins_raw = os.environ.get('CORS_ORIGINS', 'https://tev-tesoreria.onrender.com,https://tev-tesoreria-prod.onrender.com,https://tev-tesoreria-frontend.onrender.com,http://localhost:5173,http://127.0.0.1:5173')
        return [o.strip() for o in origins_raw.split(',') if o.strip()]
    elif IS_STAGING:
        origins_raw = os.environ.get('CORS_ORIGINS', 'https://tev-tesoreria-staging.onrender.com,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173')
        return [o.strip() for o in origins_raw.split(',') if o.strip()]
    return ["*"]

