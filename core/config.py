import os
from typing import List

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development').lower()
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_STAGING = ENVIRONMENT == 'staging'

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'todo-electrico-valencia-seguridad-jwt-2026-secret')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get('ACCESS_TOKEN_EXPIRE_HOURS', '12'))

MASTER_ADMIN_KEY = os.environ.get('MASTER_ADMIN_KEY', 'TEV-MASTER-RESET-2026')

def get_cors_origins() -> List[str]:
    if IS_PRODUCTION:
        origins_raw = os.environ.get('CORS_ORIGINS', 'https://tev-tesoreria.onrender.com')
        return [o.strip() for o in origins_raw.split(',') if o.strip()]
    elif IS_STAGING:
        origins_raw = os.environ.get('CORS_ORIGINS', 'https://tev-tesoreria-staging.onrender.com,http://localhost:8000,http://127.0.0.1:8000')
        return [o.strip() for o in origins_raw.split(',') if o.strip()]
    return ["*"]
