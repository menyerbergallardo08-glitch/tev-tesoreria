import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import IS_PRODUCTION, get_cors_origins, COMPANY_NAME, COMPANY_SLOGAN
from core.scheduler import start_scheduler, stop_scheduler
from database import engine, Base

# Importar Enrutadores Modulares
from routers.auth import router as auth_router
from routers.sales import router as sales_router
from routers.expenses import router as expenses_router
from routers.cxc import router as cxc_router, receivables_router
from routers.accounts import router as accounts_router
from routers.cash_close import router as cash_close_router, cash_close_legacy_router
from routers.categories import router as categories_router
from routers.transfers import router as transfers_router
from routers.audit import router as audit_router
from routers.system import router as system_router
from routers.dashboard import router as dashboard_router

# Inicializar Base de Datos
Base.metadata.create_all(bind=engine)
try:
    from init_db import init_all
    init_all()
except Exception as e:
    print(f"[WARN] init_db: {e}")

# Ciclo de Vida: Iniciar y Detener Scheduler Automático FIFO
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()

# FastAPI: API REST Pura + Entrega de Sistema de Tesorería Integral
app = FastAPI(
    title=f"{COMPANY_NAME} - Sistema de Tesorería & Flujo de Caja",
    version="2.2.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
    lifespan=lifespan
)

# CORS Estricto (Soporta Frontend Vite en localhost:5173 y producción)
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
app.include_router(receivables_router)
app.include_router(accounts_router)
app.include_router(cash_close_router)
app.include_router(cash_close_legacy_router)
app.include_router(categories_router)
app.include_router(transfers_router)
app.include_router(audit_router)
app.include_router(system_router)
app.include_router(dashboard_router)

@app.get("/health")
def root_health():
    return {
        "status": "healthy",
        "application": "OK",
        "company": COMPANY_NAME,
        "version": "2.2.0"
    }

# Servir Frontend Completo TEV (Flujo de Caja, Reportes One-Page, Mostrador, Auditoría)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "service": COMPANY_NAME,
        "slogan": COMPANY_SLOGAN,
        "status": "online",
        "version": "2.2.0"
    }



