import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from core.config import IS_PRODUCTION, get_cors_origins
from database import engine, Base

# Importar Enrutadores Modulares
from routers.auth import router as auth_router
from routers.sales import router as sales_router
from routers.expenses import router as expenses_router
from routers.cxc import router as cxc_router
from routers.accounts import router as accounts_router
from routers.cash_close import router as cash_close_router
from routers.categories import router as categories_router
from routers.transfers import router as transfers_router
from routers.audit import router as audit_router
from routers.system import router as system_router

# Inicializar Base de Datos
Base.metadata.create_all(bind=engine)
try:
    from init_db import init_all
    init_all()
except Exception as e:
    print(f"[WARN] init_db: {e}")

# Pilar 4: Cierre de Superficie de Ataque en Producción (/docs, /redoc, /openapi desactivados en Prod)
app = FastAPI(
    title="TEV Tesorería & Flujo de Caja API",
    version="2.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json"
)

# CORS Estricto
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar Enrutadores
app.include_router(auth_router)
app.include_router(sales_router)
app.include_router(expenses_router)
app.include_router(cxc_router)
app.include_router(accounts_router)
app.include_router(cash_close_router)
app.include_router(categories_router)
app.include_router(transfers_router)
app.include_router(audit_router)
app.include_router(system_router)

# Servir Frontend Modular ES6
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "TEV Tesorería API v2.0 Modular Activa"}
