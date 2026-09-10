import os
import io
import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from database import engine, SessionLocal, get_db, Base
from models import User, BudgetCategory, TreasuryAccount, Transaction, AccountMonthlyBalance, Supplier, SystemSetting, DailyCashClose, Branch, CashRegister, AuditLog
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_current_user,
    require_roles,
)

Base.metadata.create_all(bind=engine)

# Auto-inicializar tablas, usuarios base y cuentas si la base de datos (PostgreSQL / Supabase) es nueva
try:
    from init_db import init_database
    init_database()
except Exception as e:
    print(f"[WARN] Error en init_database al arrancar: {e}")


# -------------------------------------------------------------
# AUDIT LOG HELPER & BCV RATE SYNC (10/10 Enterprise Hardening)
# -------------------------------------------------------------
import json
import urllib.request

def record_audit(
    db: Session,
    user: Optional[User],
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    details: dict,
    ip_address: str = ""
):
    try:
        username = user.username if user else "sistema"
        user_id = user.id if user else None
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else "",
            details_json=json.dumps(details, ensure_ascii=False),
            ip_address=ip_address
        )
        db.add(log_entry)
        db.flush()
    except Exception as e:
        print(f"[WARN] Failed to write audit log: {e}")

def fetch_bcv_official_rate() -> Optional[float]:
    """Consulta fuentes oficiales/estandarizadas para obtener la tasa BCV en tiempo real"""
    urls = [
        "https://ve.dolarapi.com/v1/dolares/oficial",
        "https://pydolarve.org/api/v1/dollar?page=bcv"
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if "promedio" in data and isinstance(data["promedio"], (int, float)):
                        return float(data["promedio"])
                    if "monitors" in data and "bcv" in data["monitors"] and "price" in data["monitors"]["bcv"]:
                        return float(data["monitors"]["bcv"]["price"])
                    if "price" in data and isinstance(data["price"], (int, float)):
                        return float(data["price"])
        except Exception as e:
            print(f"[DEBUG] Fetch rate fallback error on {url}: {e}")
            continue
    return None

def resolve_effective_bcv_rate(db: Session) -> dict:
    """
    POLÍTICA OFICIAL DE TASA BCV - TODO ELÉCTRICO VALENCIA:
    - Lunes a Jueves a partir de las 4:30 PM:
      Se activa de inmediato la nueva tasa publicada por el BCV para resguardar las ventas de la tarde.
    - Viernes después de las 4:30 PM, Sábado y Domingo:
      Se mantiene la tasa oficial del Viernes (cierre de semana).
    - Domingo a las 12:00 de la noche (Lunes 00:01 AM):
      Se activa automáticamente la nueva tasa del Lunes emitida por el BCV.
    """
    tz_ve = datetime.timezone(datetime.timedelta(hours=-4))
    now_ve = datetime.datetime.now(tz_ve)
    weekday = now_ve.weekday() # 0=Lun, 1=Mar, 2=Mie, 3=Jue, 4=Vie, 5=Sab, 6=Dom
    current_minutes = now_ve.hour * 60 + now_ve.minute
    cutoff_430 = 16 * 60 + 30 # 4:30 PM = 990 minutos

    fresh_rate = fetch_bcv_official_rate()
    
    # Obtener tasa guardada actualmente y tasa congelada de viernes si aplica
    setting_active = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv').first()
    setting_friday = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv_viernes').first()
    setting_next_monday = db.query(SystemSetting).filter(SystemSetting.key == 'tasa_bcv_proximo_lunes').first()

    current_val = float(setting_active.value) if (setting_active and setting_active.value) else 36.80
    
    # 1. Regla de Viernes por la tarde (después de 4:30 PM) y fin de semana (Sábado y Domingo antes de 00:00 Lunes)
    if weekday == 4 and current_minutes >= cutoff_430:
        # Es Viernes después de las 4:30 PM -> Guardar la nueva tasa para el Lunes, pero mantener vigente la del Viernes
        if fresh_rate and fresh_rate > 0:
            if not setting_friday:
                db.add(SystemSetting(key='tasa_bcv_viernes', value=str(current_val)))
            else:
                setting_friday.value = str(current_val)
            
            if not setting_next_monday:
                db.add(SystemSetting(key='tasa_bcv_proximo_lunes', value=str(fresh_rate)))
            else:
                setting_next_monday.value = str(fresh_rate)
            db.commit()
            
        return {
            "rate": current_val,
            "policy_applied": "Viernes tarde / Fin de semana (Se mantiene tasa de cierre del Viernes hasta el Domingo 12:00 de la noche)",
            "next_rate_monday": float(setting_next_monday.value) if setting_next_monday else fresh_rate,
            "synced": True
        }

    elif weekday in (5, 6):
        # Es Sábado o Domingo antes de medianoche
        friday_val = float(setting_friday.value) if (setting_friday and setting_friday.value) else current_val
        return {
            "rate": friday_val,
            "policy_applied": "Fin de Semana (Operando con tasa de Viernes)",
            "next_rate_monday": float(setting_next_monday.value) if setting_next_monday else fresh_rate,
            "synced": True
        }

    # 2. Regla de Lunes a Jueves (o Lunes desde las 00:01 AM)
    # Si es Lunes después de medianoche y teníamos tasa guardada para el lunes, la aplicamos
    effective_rate = fresh_rate or current_val
    if weekday == 0 and setting_next_monday and setting_next_monday.value:
        effective_rate = float(setting_next_monday.value)
    elif fresh_rate and fresh_rate > 0:
        effective_rate = fresh_rate

    # Actualizar tasa activa en el sistema
    if not setting_active:
        setting_active = SystemSetting(key='tasa_bcv', value=str(effective_rate))
        db.add(setting_active)
    else:
        setting_active.value = str(effective_rate)
        setting_active.updated_at = datetime.datetime.utcnow()

    setting2 = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    if setting2:
        setting2.value = str(effective_rate)
    
    db.commit()

    is_vespertina = (weekday in (0, 1, 2, 3) and current_minutes >= cutoff_430)
    policy_msg = "Tasa Vespertina Activa (Lunes-Jueves después de 4:30 PM)" if is_vespertina else "Tasa Oficial Activa del Día"

    return {
        "rate": effective_rate,
        "policy_applied": policy_msg,
        "synced": True
    }


app = FastAPI(
    title="Todo Eléctrico Valencia - Sistema de Tesorería, Gastos y Flujo de Caja",
    version="1.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Todo Eléctrico Valencia API Activa."}


# -------------------------------------------------------------
# Schemas Pydantic
# -------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: str

class ResetPasswordRequest(BaseModel):
    new_password: str

class CategoryResponse(BaseModel):
    id: int
    code: int
    name: str
    monthly_budget_usd: float
    is_active: bool

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    monthly_budget_usd: Optional[float] = None
    is_active: Optional[bool] = None

class CategoryCreate(BaseModel):
    code: int
    name: str
    monthly_budget_usd: float = 0.0

class AccountCreate(BaseModel):
    name: str
    currency: str = "USD"
    account_type: str = "Caja Operativa"
    initial_balance: float = 0.0

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    currency: Optional[str] = None
    account_type: Optional[str] = None
    initial_balance: Optional[float] = None
    is_active: Optional[bool] = None

class TransactionCreate(BaseModel):
    date: datetime.date
    movement_type: str  # 'INGRESO', 'EGRESO'
    subtype: str
    account_id: int
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None
    amount_original: float
    currency: str
    exchange_rate: float = 1.0
    amount_usd: Optional[float] = None
    reference_number: Optional[str] = ""
    beneficiary: Optional[str] = ""
    description: Optional[str] = ""
    doc_type: Optional[str] = "FACTURA_FISCAL"
    doc_number: Optional[str] = ""
    is_credit: Optional[bool] = False
    credit_status: Optional[str] = "PAGADO"
    tax_retention_amount: Optional[float] = 0.0
    tax_retention_proof: Optional[str] = ""
    pos_terminal: Optional[str] = ""
    pos_lot_number: Optional[str] = ""



# -------------------------------------------------------------
# Schemas para Venta en Caliente y Abonos CxC
# -------------------------------------------------------------
class LiveSaleCreate(BaseModel):
    date: datetime.date
    doc_type: str  # 'FACTURA_FISCAL', 'NOTA_ENTREGA', 'DEVOLUCION'
    doc_number: str
    client_name: str
    client_rif: Optional[str] = ""
    is_credit: bool = False
    amount_original: float
    currency: str = "USD"  # 'USD', 'VES'
    exchange_rate: Optional[float] = 1.0
    account_id: Optional[int] = None  # None if credit
    pos_terminal: Optional[str] = ""
    pos_lot_number: Optional[str] = ""
    tax_retention_amount: Optional[float] = 0.0
    tax_retention_proof: Optional[str] = ""
    reference_number: Optional[str] = ""
    description: Optional[str] = ""

class AbonoCreate(BaseModel):
    date: datetime.date
    amount_original: float
    currency: str = "USD"
    exchange_rate: Optional[float] = 1.0
    account_id: int
    pos_terminal: Optional[str] = ""
    pos_lot_number: Optional[str] = ""
    reference_number: Optional[str] = ""
    tax_retention_amount: Optional[float] = 0.0
    tax_retention_proof: Optional[str] = ""
    description: Optional[str] = ""

class DailyCashCloseCreate(BaseModel):
    date: datetime.date
    cajero_name: str
    verified_by: Optional[str] = "Administración"
    status: Optional[str] = "CUADRADO"
    profit_sales_total_usd: Optional[float] = 0.0
    sales_fiscal_iva_usd: Optional[float] = 0.0
    sales_notes_credit_usd: Optional[float] = 0.0
    sales_notes_collected_usd: Optional[float] = 0.0
    returns_total_usd: Optional[float] = 0.0
    net_sales_usd: Optional[float] = 0.0
    cash_usd_physical: Optional[float] = 0.0
    cash_ves_physical: Optional[float] = 0.0
    pos_total_usd: Optional[float] = 0.0
    bank_transfers_usd: Optional[float] = 0.0
    cashea_usd: Optional[float] = 0.0
    retentions_iva_usd: Optional[float] = 0.0
    retentions_islr_usd: Optional[float] = 0.0
    expenses_caja_usd: Optional[float] = 0.0
    total_collected_real_usd: Optional[float] = 0.0
    total_expected_usd: Optional[float] = 0.0
    difference_usd: Optional[float] = 0.0
    arqueo_usd_json: Optional[str] = "{}"
    arqueo_ves_json: Optional[str] = "{}"
    pos_details_json: Optional[str] = "{}"
    notes: Optional[str] = ""

class TransferCreate(BaseModel):
    date: datetime.date
    origin_account_id: int
    destination_account_id: int
    amount_origin: float
    amount_destination: float
    exchange_rate: float = 1.0
    reference_number: Optional[str] = ""
    description: Optional[str] = "Traspaso / Cambio de divisas"

class InitialBalanceItem(BaseModel):
    account_id: int
    initial_balance: float

class SetInitialBalancesRequest(BaseModel):
    month: str  # 'YYYY-MM'
    balances: List[InitialBalanceItem]


# -------------------------------------------------------------
# Auth & User Management Endpoints
# -------------------------------------------------------------
@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos. Verifique sus datos.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado. Contacte a la Dirección.",
        )

    token = create_access_token(data={"sub": user.username, "role": user.role, "id": user.id})
    return LoginResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@app.post("/api/auth/change-password")
def change_own_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual ingresada es incorrecta.")
    if len(req.new_password) < 4:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 4 caracteres.")

    current_user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"success": True, "message": "Contraseña actualizada exitosamente."}

@app.get("/api/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["directivo"]))
):
    users = db.query(User).order_by(User.id).all()
    return [UserResponse.model_validate(u) for u in users]

@app.post("/api/users", response_model=UserResponse)
def create_user(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["directivo"]))
):
    existing = db.query(User).filter(User.username == req.username.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"El nombre de usuario '{req.username}' ya existe.")
    if req.role not in ["cajera", "administradora", "directivo"]:
        raise HTTPException(status_code=400, detail="Rol inválido. Debe ser: cajera, administradora o directivo.")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 4 caracteres.")

    new_user = User(
        username=req.username.strip(),
        password_hash=hash_password(req.password),
        full_name=req.full_name.strip(),
        role=req.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)

@app.patch("/api/users/{user_id}/password")
def reset_user_password(
    user_id: int,
    req: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["directivo"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if len(req.new_password) < 4:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 4 caracteres.")

    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"success": True, "message": f"Contraseña restablecida para el usuario {user.username}."}

@app.patch("/api/users/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["directivo"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puede desactivar su propio usuario.")

    user.is_active = not user.is_active
    db.commit()
    return {"success": True, "is_active": user.is_active, "message": f"Estado del usuario {user.username} actualizado."}


# -------------------------------------------------------------
# Treasury Accounts & Monthly Initial Balances
# -------------------------------------------------------------
@app.get("/api/accounts")
def get_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accounts = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).all()
    res = []
    for acc in accounts:
        ingresos = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.movement_type == "INGRESO",
            Transaction.status != "ANULADO"
        ).scalar()

        egresos = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.movement_type == "EGRESO",
            Transaction.status != "ANULADO"
        ).scalar()

        calc_balance = acc.initial_balance + ingresos - egresos

        res.append({
            "id": acc.id,
            "name": acc.name,
            "currency": acc.currency,
            "account_type": acc.account_type,
            "initial_balance": acc.initial_balance,
            "current_balance": round(calc_balance, 2),
            "only_income": getattr(acc, 'only_income', False) or ('CASHEA' in acc.name.upper()),
            "is_active": acc.is_active
        })
    return res

@app.post("/api/accounts")
def create_account(
    acc_in: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    account = TreasuryAccount(
        name=acc_in.name.strip(),
        currency=acc_in.currency.upper(),
        account_type=acc_in.account_type,
        initial_balance=acc_in.initial_balance,
        is_active=True
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

@app.put("/api/accounts/{id}")
def update_account(
    id: int,
    acc_in: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if acc_in.name is not None:
        acc.name = acc_in.name.strip()
    if acc_in.currency is not None:
        acc.currency = acc_in.currency.upper()
    if acc_in.account_type is not None:
        acc.account_type = acc_in.account_type
    if acc_in.initial_balance is not None:
        acc.initial_balance = acc_in.initial_balance
    if acc_in.is_active is not None:
        acc.is_active = acc_in.is_active
    db.commit()
    db.refresh(acc)
    return acc

@app.get("/api/accounts/monthly-balances")
def get_monthly_balances(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    accounts = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).all()
    res = []
    for acc in accounts:
        rec = db.query(AccountMonthlyBalance).filter(
            AccountMonthlyBalance.account_id == acc.id,
            AccountMonthlyBalance.month == month
        ).first()
        init_val = rec.initial_balance if rec else acc.initial_balance
        res.append({
            "account_id": acc.id,
            "name": acc.name,
            "currency": acc.currency,
            "initial_balance": init_val
        })
    return {"month": month, "balances": res}

@app.post("/api/accounts/monthly-balances")
def set_monthly_balances(
    req: SetInitialBalancesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    for item in req.balances:
        rec = db.query(AccountMonthlyBalance).filter(
            AccountMonthlyBalance.account_id == item.account_id,
            AccountMonthlyBalance.month == req.month
        ).first()
        if rec:
            rec.initial_balance = item.initial_balance
        else:
            rec = AccountMonthlyBalance(
                account_id=item.account_id,
                month=req.month,
                initial_balance=item.initial_balance
            )
            db.add(rec)
    db.commit()
    return {"success": True, "message": f"Saldos iniciales para {req.month} actualizados correctamente."}


# -------------------------------------------------------------
# DEDICATED CASH FLOW ENDPOINTS (Flujo de Caja Mensual y Anual)
# -------------------------------------------------------------
@app.get("/api/dashboard/cash-flow")
def get_cash_flow(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    try:
        year, m = map(int, month.split("-"))
        start_date = datetime.date(year, m, 1)
        if m == 12:
            end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de mes inválido. Use YYYY-MM.")

    accounts = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).all()

    avg_rate_rec = db.query(func.avg(Transaction.exchange_rate)).filter(
        Transaction.currency == "VES",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.status != "ANULADO"
    ).scalar()
    month_avg_rate = float(avg_rate_rec) if avg_rate_rec and avg_rate_rec > 0 else 756.71

    accounts_detail = []
    total_initial_usd = 0.0
    total_final_usd = 0.0

    total_usd_cash = 0.0
    total_ves_bank = 0.0
    total_usdt = 0.0

    for acc in accounts:
        m_rec = db.query(AccountMonthlyBalance).filter(
            AccountMonthlyBalance.account_id == acc.id,
            AccountMonthlyBalance.month == month
        ).first()
        init_bal = m_rec.initial_balance if m_rec else acc.initial_balance

        ingresos_orig = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.movement_type == "INGRESO",
            Transaction.subtype != "TRASPASO_ENTRADA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        egresos_orig = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.movement_type == "EGRESO",
            Transaction.subtype != "TRASPASO_SALIDA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        traspasos_in = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.subtype == "TRASPASO_ENTRADA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        traspasos_out = db.query(func.coalesce(func.sum(Transaction.amount_original), 0.0)).filter(
            Transaction.account_id == acc.id,
            Transaction.subtype == "TRASPASO_SALIDA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        final_orig = init_bal + ingresos_orig - egresos_orig + traspasos_in - traspasos_out

        if acc.currency == "USD":
            init_usd = init_bal
            final_usd = final_orig
            total_usd_cash += final_orig
        elif acc.currency == "USDT":
            init_usd = init_bal
            final_usd = final_orig
            total_usdt += final_orig
        else:
            init_usd = init_bal / month_avg_rate
            final_usd = final_orig / month_avg_rate
            total_ves_bank += final_orig

        total_initial_usd += init_usd
        total_final_usd += final_usd

        accounts_detail.append({
            "account_id": acc.id,
            "name": acc.name,
            "currency": acc.currency,
            "account_type": acc.account_type,
            "initial_balance": round(init_bal, 2),
            "inflows_orig": round(ingresos_orig, 2),
            "outflows_orig": round(egresos_orig, 2),
            "transfers_net_orig": round(traspasos_in - traspasos_out, 2),
            "final_balance": round(final_orig, 2),
            "initial_balance_usd": round(init_usd, 2),
            "final_balance_usd": round(final_usd, 2)
        })

    # Ingresos Operativos en USD
    ventas_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "INGRESO",
        Transaction.subtype == "VENTA_DIARIA",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    cobros_cxc_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "INGRESO",
        Transaction.subtype == "COBRO_CXC",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    otros_ingresos_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "INGRESO",
        Transaction.subtype.notin_(["VENTA_DIARIA", "COBRO_CXC", "TRASPASO_ENTRADA"]),
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    total_inflows_usd = ventas_usd + cobros_cxc_usd + otros_ingresos_usd

    # Egresos Operativos en USD (Desglose por partidas presupuestarias y proveedores)
    categories = db.query(BudgetCategory).filter(BudgetCategory.is_active == True).order_by(BudgetCategory.code).all()
    categories_breakdown = []
    total_gastos_op_usd = 0.0
    for cat in categories:
        cat_spent = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.category_id == cat.id,
            Transaction.movement_type == "EGRESO",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()
        total_gastos_op_usd += cat_spent
        if cat_spent > 0 or cat.monthly_budget_usd > 0:
            categories_breakdown.append({
                "code": cat.code,
                "name": cat.name,
                "spent_usd": round(cat_spent, 2)
            })

    pagos_prov_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "EGRESO",
        Transaction.subtype == "PAGO_PROVEEDOR",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    otros_egresos_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.movement_type == "EGRESO",
        Transaction.subtype.notin_(["GASTO_OPERATIVO", "PAGO_PROVEEDOR", "TRASPASO_SALIDA"]),
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    total_outflows_usd = total_gastos_op_usd + pagos_prov_usd + otros_egresos_usd

    # Diferencial Cambiario de Traspasos
    traspasos_out_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.subtype == "TRASPASO_SALIDA",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    traspasos_in_usd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.subtype == "TRASPASO_ENTRADA",
        Transaction.status != "ANULADO",
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).scalar()

    fx_differential_usd = traspasos_in_usd - traspasos_out_usd

    net_operational_cash_flow = total_inflows_usd - total_outflows_usd
    net_total_cash_flow = net_operational_cash_flow + fx_differential_usd

    return {
        "month": month,
        "period_label": f"{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}",
        "initial_balance_usd": round(total_initial_usd, 2),
        "total_inflows_usd": round(total_inflows_usd, 2),
        "inflows_breakdown": {
            "ventas_usd": round(ventas_usd, 2),
            "cobros_cxc_usd": round(cobros_cxc_usd, 2),
            "otros_ingresos_usd": round(otros_ingresos_usd, 2)
        },
        "total_outflows_usd": round(total_outflows_usd, 2),
        "outflows_breakdown": {
            "gastos_operativos_usd": round(total_gastos_op_usd, 2),
            "pagos_proveedores_usd": round(pagos_prov_usd, 2),
            "otros_egresos_usd": round(otros_egresos_usd, 2),
            "categories": categories_breakdown
        },
        "fx_differential_usd": round(fx_differential_usd, 2),
        "net_operational_flow_usd": round(net_operational_cash_flow, 2),
        "net_cash_flow_usd": round(net_total_cash_flow, 2),
        "final_balance_usd": round(total_final_usd, 2),
        "currency_summary": {
            "usd_cash": round(total_usd_cash, 2),
            "ves_bank": round(total_ves_bank, 2),
            "usdt": round(total_usdt, 2),
            "rate_used": round(month_avg_rate, 2)
        },
        "accounts_detail": accounts_detail
    }


@app.get("/api/dashboard/cash-flow-annual")
def get_annual_cash_flow(
    year: int = Query(2026),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    # Genera la matriz de Enero a Diciembre como en la Imagen 5
    months_labels = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    matrix_data = []

    for idx, label in enumerate(months_labels, 1):
        m_str = f"{year}-{idx:02d}"
        start_d = datetime.date(year, idx, 1)
        if idx == 12:
            end_d = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_d = datetime.date(year, idx + 1, 1) - datetime.timedelta(days=1)

        # Ingresos
        ventas = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "INGRESO",
            Transaction.subtype == "VENTA_DIARIA",
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        cxc = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "INGRESO",
            Transaction.subtype == "COBRO_CXC",
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        otros_in = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "INGRESO",
            Transaction.subtype.notin_(["VENTA_DIARIA", "COBRO_CXC", "TRASPASO_ENTRADA"]),
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        # Egresos
        gastos = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "EGRESO",
            Transaction.subtype == "GASTO_OPERATIVO",
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        prov = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "EGRESO",
            Transaction.subtype == "PAGO_PROVEEDOR",
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        otros_out = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.movement_type == "EGRESO",
            Transaction.subtype.notin_(["GASTO_OPERATIVO", "PAGO_PROVEEDOR", "TRASPASO_SALIDA"]),
            Transaction.status != "ANULADO",
            Transaction.date >= start_d,
            Transaction.date <= end_d
        ).scalar()

        tot_in = ventas + cxc + otros_in
        tot_out = gastos + prov + otros_out
        net = tot_in - tot_out

        matrix_data.append({
            "month_index": idx,
            "month_label": label,
            "ventas": round(ventas, 2),
            "cxc": round(cxc, 2),
            "otros_in": round(otros_in, 2),
            "total_in": round(tot_in, 2),
            "gastos": round(gastos, 2),
            "prov": round(prov, 2),
            "otros_out": round(otros_out, 2),
            "total_out": round(tot_out, 2),
            "net": round(net, 2)
        })

    return {"year": year, "months": matrix_data}


@app.get("/api/dashboard/cash-flow-daily")
def get_daily_cash_flow(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    year, m = map(int, month.split("-"))
    start_date = datetime.date(year, m, 1)
    if m == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)

    txs = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.status != "ANULADO"
    ).order_by(Transaction.date.asc()).all()

    days_map = {}
    cur_date = start_date
    while cur_date <= end_date:
        d_key = cur_date.isoformat()
        days_map[d_key] = {
            "date": d_key,
            "day_num": cur_date.day,
            "ventas": 0.0,
            "cxc": 0.0,
            "otros_in": 0.0,
            "total_in": 0.0,
            "gastos": 0.0,
            "prov": 0.0,
            "otros_out": 0.0,
            "total_out": 0.0,
            "net": 0.0,
            "count": 0
        }
        cur_date += datetime.timedelta(days=1)

    tot_ventas = 0.0
    tot_cxc = 0.0
    tot_otros_in = 0.0
    tot_gastos = 0.0
    tot_prov = 0.0
    tot_otros_out = 0.0

    for t in txs:
        d_str = t.date.isoformat()
        if d_str in days_map:
            days_map[d_str]["count"] += 1
            if t.movement_type == "INGRESO":
                if t.subtype == "VENTA_DIARIA":
                    days_map[d_str]["ventas"] += t.amount_usd
                    tot_ventas += t.amount_usd
                elif t.subtype == "COBRO_CXC":
                    days_map[d_str]["cxc"] += t.amount_usd
                    tot_cxc += t.amount_usd
                elif t.subtype != "TRASPASO_ENTRADA":
                    days_map[d_str]["otros_in"] += t.amount_usd
                    tot_otros_in += t.amount_usd
            elif t.movement_type == "EGRESO":
                if t.subtype == "GASTO_OPERATIVO":
                    days_map[d_str]["gastos"] += t.amount_usd
                    tot_gastos += t.amount_usd
                elif t.subtype == "PAGO_PROVEEDOR":
                    days_map[d_str]["prov"] += t.amount_usd
                    tot_prov += t.amount_usd
                elif t.subtype != "TRASPASO_SALIDA":
                    days_map[d_str]["otros_out"] += t.amount_usd
                    tot_otros_out += t.amount_usd

    result = []
    for d_str, val in sorted(days_map.items()):
        val["ventas"] = round(val["ventas"], 2)
        val["cxc"] = round(val["cxc"], 2)
        val["otros_in"] = round(val["otros_in"], 2)
        val["total_in"] = round(val["ventas"] + val["cxc"] + val["otros_in"], 2)

        val["gastos"] = round(val["gastos"], 2)
        val["prov"] = round(val["prov"], 2)
        val["otros_out"] = round(val["otros_out"], 2)
        val["total_out"] = round(val["gastos"] + val["prov"] + val["otros_out"], 2)

        val["net"] = round(val["total_in"] - val["total_out"], 2)
        result.append(val)

    tot_in_final = tot_ventas + tot_cxc + tot_otros_in
    tot_out_final = tot_gastos + tot_prov + tot_otros_out
    totals = {
        "ventas": round(tot_ventas, 2),
        "cxc": round(tot_cxc, 2),
        "otros_in": round(tot_otros_in, 2),
        "total_in": round(tot_in_final, 2),
        "gastos": round(tot_gastos, 2),
        "prov": round(tot_prov, 2),
        "otros_out": round(tot_otros_out, 2),
        "total_out": round(tot_out_final, 2),
        "net": round(tot_in_final - tot_out_final, 2)
    }

    return {"month": month, "days": result, "totals": totals}


# -------------------------------------------------------------
# Budget Categories Endpoints
# -------------------------------------------------------------
@app.get("/api/categories")
def get_categories(
    month: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(BudgetCategory)
    if not include_inactive:
        query = query.filter(BudgetCategory.is_active == True)
    categories = query.order_by(BudgetCategory.code).all()
    
    if month:
        try:
            year, m = map(int, month.split("-"))
            start_date = datetime.date(year, m, 1)
            if m == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)
        except Exception:
            start_date = datetime.date(2026, 8, 1)
            end_date = datetime.date(2026, 8, 31)
    else:
        start_date = datetime.date(2026, 8, 1)
        end_date = datetime.date(2026, 8, 31)

    result = []
    for cat in categories:
        spent = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
            Transaction.category_id == cat.id,
            Transaction.movement_type == "EGRESO",
            Transaction.status != "ANULADO",
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()

        remaining = cat.monthly_budget_usd - spent
        pct = (spent / cat.monthly_budget_usd * 100) if cat.monthly_budget_usd > 0 else 0.0
        status_alert = "ALERTA" if remaining <= 0 and cat.monthly_budget_usd > 0 else "APTO"

        result.append({
            "id": cat.id,
            "code": cat.code,
            "name": cat.name,
            "monthly_budget_usd": cat.monthly_budget_usd,
            "spent_usd": round(spent, 2),
            "remaining_usd": round(remaining, 2),
            "percentage_spent": round(pct, 1),
            "status": status_alert,
            "is_active": cat.is_active
        })
    return result

@app.post("/api/categories")
def create_category(
    cat_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    existing = db.query(BudgetCategory).filter(BudgetCategory.code == cat_in.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe una partida con el código {cat_in.code}")
    new_cat = BudgetCategory(
        code=cat_in.code,
        name=cat_in.name,
        monthly_budget_usd=cat_in.monthly_budget_usd,
        is_active=True
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@app.put("/api/categories/{id}")
def update_category(
    id: int,
    cat_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    cat = db.query(BudgetCategory).filter(BudgetCategory.id == id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Partida presupuestaria no encontrada")
    if cat_in.name is not None:
        cat.name = cat_in.name
    if cat_in.monthly_budget_usd is not None:
        cat.monthly_budget_usd = cat_in.monthly_budget_usd
    if cat_in.is_active is not None:
        cat.is_active = cat_in.is_active
    db.commit()
    db.refresh(cat)
    return cat


# -------------------------------------------------------------
# System Settings & BCV Rate Endpoints
# -------------------------------------------------------------
class BcvRateUpdate(BaseModel):
    rate: float

@app.get("/api/settings/bcv-rate")
def get_bcv_rate(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    rate_val = float(setting.value) if (setting and setting.value) else 36.80
    return {
        "rate": rate_val,
        "updated_at": setting.updated_at.isoformat() if setting and setting.updated_at else None,
        "updated_by": setting.updated_by if setting else "sistema"
    }

@app.post("/api/settings/bcv-rate")
def update_bcv_rate(
    payload: BcvRateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    if payload.rate <= 0:
        raise HTTPException(status_code=400, detail="La tasa debe ser mayor a 0.00")
    setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    if not setting:
        setting = SystemSetting(key='bcv_rate', value=str(payload.rate), updated_by=current_user.username)
        db.add(setting)
    else:
        setting.value = str(payload.rate)
        setting.updated_by = current_user.username
        setting.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": "Tasa BCV actualizada exitosamente", "rate": payload.rate}


# -------------------------------------------------------------
# Suppliers (Proveedores) Endpoints
# -------------------------------------------------------------
class SupplierCreate(BaseModel):
    name: str
    rif: Optional[str] = None
    phone: Optional[str] = None
    bank_details: Optional[str] = None

@app.get("/api/suppliers")
def get_suppliers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name.asc()).all()

@app.post("/api/suppliers")
def create_supplier(
    sup_in: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    name = sup_in.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre del proveedor es obligatorio.")
    existing = db.query(Supplier).filter(Supplier.name.ilike(name), Supplier.is_active == True).first()
    if existing:
        return existing
    supplier = Supplier(
        name=name,
        rif=sup_in.rif.strip().upper() if sup_in.rif else None,
        phone=sup_in.phone.strip() if sup_in.phone else None,
        bank_details=sup_in.bank_details.strip() if sup_in.bank_details else "",
        is_active=True
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


# -------------------------------------------------------------
# Transactions Endpoints (Double-entry transfers)
# -------------------------------------------------------------
@app.get("/api/transactions")
def list_transactions(
    date: Optional[datetime.date] = None,
    month: Optional[str] = None,
    movement_type: Optional[str] = None,
    subtype: Optional[str] = None,
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Transaction)

    if date:
        q = q.filter(Transaction.date == date)
    elif month:
        try:
            year, m = map(int, month.split("-"))
            start_date = datetime.date(year, m, 1)
            if m == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)
            q = q.filter(Transaction.date >= start_date, Transaction.date <= end_date)
        except Exception:
            pass

    if movement_type:
        q = q.filter(Transaction.movement_type == movement_type)
    if subtype:
        q = q.filter(Transaction.subtype == subtype)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if status_filter:
        q = q.filter(Transaction.status == status_filter)

    total = q.count()
    txs = q.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(offset).limit(limit).all()

    items = []
    for t in txs:
        items.append({
            "id": t.id,
            "date": t.date.isoformat(),
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
            "movement_type": t.movement_type,
            "subtype": t.subtype,
            "account_id": t.account_id,
            "account_name": t.account.name if t.account else "",
            "destination_account_id": t.destination_account_id,
            "destination_account_name": t.destination_account.name if t.destination_account else None,
            "category_id": t.category_id,
            "category_name": t.category.name if t.category else None,
            "category_code": t.category.code if t.category else None,
            "amount_original": round(t.amount_original, 2),
            "currency": t.currency,
            "exchange_rate": round(t.exchange_rate, 2),
            "amount_usd": round(t.amount_usd, 2),
            "reference_number": t.reference_number,
            "beneficiary": t.beneficiary,
            "description": t.description,
            "status": t.status,
            "created_by": t.creator.full_name if t.creator else "Sistema",
            "verified_by": t.verifier.full_name if t.verifier else None
        })

    return {"total": total, "items": items}


@app.post("/api/transactions")
def create_transaction(
    tx_in: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if tx_in.amount_original <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a cero.")

    # 1. Restricción para cajeras: No pueden hacer cambios de divisas ni traspasos
    if current_user.role == "cajera" and (tx_in.subtype == "CAMBIO_DIVISAS" or tx_in.movement_type == "TRASPASO"):
        raise HTTPException(status_code=403, detail="Los usuarios de caja no tienen permiso para registrar cambios de divisas ni traspasos.")

    account = db.query(TreasuryAccount).filter(TreasuryAccount.id == tx_in.account_id).first()
    if not account:
        raise HTTPException(status_code=400, detail="La cuenta de tesorería seleccionada no existe.")

    # 2. Restricción Cashea: Solo para ingresos
    if (getattr(account, 'only_income', False) or 'CASHEA' in account.name.upper()) and tx_in.movement_type == "EGRESO":
        raise HTTPException(status_code=400, detail=f"La cuenta '{account.name}' está configurada exclusivamente para registrar INGRESOS.")

    # Control estricto de duplicados por referencia bancaria (en todas las cuentas)
    if tx_in.reference_number and len(tx_in.reference_number.strip()) > 2 and tx_in.subtype != "VENTA_DIARIA":
        ref = tx_in.reference_number.strip()
        dup = db.query(Transaction).filter(
            Transaction.reference_number.ilike(ref),
            Transaction.status != "ANULADO"
        ).first()
        if dup:
            acc_name = dup.account.name if dup.account else "Desconocida"
            raise HTTPException(
                status_code=400,
                detail=f"¡ALERTA DE PAGO DUPLICADO! La referencia bancaria '{ref}' ya fue registrada el {dup.date} por ${dup.amount_usd:.2f} en '{acc_name}' (Beneficiario: {dup.beneficiary}). Verifique para evitar pagos duplicados."
            )

    # 3. Tasa BCV Oficial Obligatoria (salvo cambio de divisas que es negociado)
    bcv_setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    active_bcv = float(bcv_setting.value) if (bcv_setting and bcv_setting.value) else 36.80

    if tx_in.currency == "VES":
        if tx_in.subtype != "CAMBIO_DIVISAS":
            rate = active_bcv
        else:
            rate = tx_in.exchange_rate if tx_in.exchange_rate > 0 else active_bcv
        calc_usd = round(tx_in.amount_original / rate, 2)
    elif tx_in.currency in ["USD", "USDT"]:
        calc_usd = round(tx_in.amount_original, 2)
        rate = 1.0
    else:
        calc_usd = tx_in.amount_usd or tx_in.amount_original

    if tx_in.subtype == "GASTO_OPERATIVO" and not tx_in.category_id:
        raise HTTPException(status_code=400, detail="Para un gasto operativo debe seleccionar la Partida Presupuestaria correspondiente.")

    # Adaptación para Venta Diaria
    benef = tx_in.beneficiary.strip() if tx_in.beneficiary else ""
    desc = tx_in.description.strip() if tx_in.description else ""
    if tx_in.subtype == "VENTA_DIARIA":
        if not benef:
            benef = "Ventas Mostrador - Tienda Valencia"
        if not desc:
            desc = f"Cierre de ventas del día ({account.name})"

    tx = Transaction(
        date=tx_in.date,
        movement_type=tx_in.movement_type,
        subtype=tx_in.subtype,
        account_id=account.id,
        destination_account_id=tx_in.destination_account_id,
        category_id=tx_in.category_id,
        amount_original=tx_in.amount_original,
        currency=tx_in.currency,
        exchange_rate=rate,
        amount_usd=calc_usd,
        reference_number=tx_in.reference_number.strip() if tx_in.reference_number else "",
        beneficiary=benef,
        description=desc,
        doc_type=tx_in.doc_type or "FACTURA_FISCAL",
        doc_number=tx_in.doc_number.strip() if tx_in.doc_number else "",
        is_credit=tx_in.is_credit or False,
        credit_status="PENDIENTE" if tx_in.is_credit else "PAGADO",
        tax_retention_amount=tx_in.tax_retention_amount or 0.0,
        tax_retention_proof=tx_in.tax_retention_proof.strip() if tx_in.tax_retention_proof else "",
        pos_terminal=tx_in.pos_terminal.strip() if tx_in.pos_terminal else "",
        pos_lot_number=tx_in.pos_lot_number.strip() if tx_in.pos_lot_number else "",
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx)
    record_audit(
        db,
        current_user,
        "ABONO_CXC",
        "Transaction",
        str(tx.id),
        {
            "parent_id": parent.id,
            "parent_doc": parent.doc_number,
            "abono_usd": calc_usd,
            "remaining_usd": rem,
            "client": parent.client_name
        }
    )
    db.commit()
    db.refresh(tx)

    return {
        "success": True,
        "message": "Movimiento registrado exitosamente",
        "id": tx.id,
        "amount_usd": tx.amount_usd
    }


@app.post("/api/transactions/transfer")
def create_transfer(
    trans_in: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Traspaso contable por Partida Doble entre Cuentas de Tesorería
    if trans_in.origin_account_id == trans_in.destination_account_id:
        raise HTTPException(status_code=400, detail="La cuenta de origen y destino no pueden ser la misma.")
    if trans_in.amount_origin <= 0 or trans_in.amount_destination <= 0:
        raise HTTPException(status_code=400, detail="Los montos deben ser mayores a cero.")

    acc_orig = db.query(TreasuryAccount).filter(TreasuryAccount.id == trans_in.origin_account_id).first()
    acc_dest = db.query(TreasuryAccount).filter(TreasuryAccount.id == trans_in.destination_account_id).first()
    if not acc_orig or not acc_dest:
        raise HTTPException(status_code=400, detail="Una de las cuentas seleccionadas no existe.")

    rate = trans_in.exchange_rate if trans_in.exchange_rate > 0 else 1.0

    # Calcular equivalente en USD para cada lado
    if acc_orig.currency == "USD" or acc_orig.currency == "USDT":
        orig_usd = trans_in.amount_origin
    else:
        orig_usd = round(trans_in.amount_origin / rate, 2)

    if acc_dest.currency == "USD" or acc_dest.currency == "USDT":
        dest_usd = trans_in.amount_destination
    else:
        dest_usd = round(trans_in.amount_destination / rate, 2)

    # 1. Asiento 1: Egreso de Cuenta Origen
    tx_out = Transaction(
        date=trans_in.date,
        movement_type="EGRESO",
        subtype="TRASPASO_SALIDA",
        account_id=acc_orig.id,
        destination_account_id=acc_dest.id,
        amount_original=trans_in.amount_origin,
        currency=acc_orig.currency,
        exchange_rate=rate,
        amount_usd=orig_usd,
        reference_number=trans_in.reference_number or "",
        beneficiary=f"Hacia: {acc_dest.name}",
        description=f"Salida por Traspaso/Cambio hacia {acc_dest.name}. {trans_in.description or ''}".strip(),
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx_out)

    # 2. Asiento 2: Ingreso a Cuenta Destino (Partida Doble)
    tx_in = Transaction(
        date=trans_in.date,
        movement_type="INGRESO",
        subtype="TRASPASO_ENTRADA",
        account_id=acc_dest.id,
        destination_account_id=acc_orig.id,
        amount_original=trans_in.amount_destination,
        currency=acc_dest.currency,
        exchange_rate=rate,
        amount_usd=dest_usd,
        reference_number=trans_in.reference_number or "",
        beneficiary=f"Desde: {acc_orig.name}",
        description=f"Entrada por Traspaso/Cambio desde {acc_orig.name}. {trans_in.description or ''}".strip(),
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx_in)
    db.commit()

    return {
        "success": True,
        "message": f"Traspaso de fondos registrado con éxito: {trans_in.amount_origin} {acc_orig.currency} -> {trans_in.amount_destination} {acc_dest.currency}",
        "out_id": tx_out.id,
        "in_id": tx_in.id
    }


@app.patch("/api/transactions/{id}/verify")
def verify_transaction(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    tx = db.query(Transaction).filter(Transaction.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    tx.status = "VERIFICADO"
    tx.verified_by_id = current_user.id
    db.commit()
    return {"success": True, "message": f"Movimiento #{id} marcado como VERIFICADO"}


@app.delete("/api/transactions/{id}")
def cancel_transaction(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    tx = db.query(Transaction).filter(Transaction.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    tx.status = "ANULADO"
    db.commit()
    return {"success": True, "message": f"Movimiento #{id} ha sido ANULADO"}


# -------------------------------------------------------------
# Daily Closing / Arqueo
# -------------------------------------------------------------
@app.get("/api/dashboard/daily-closing")
def get_daily_closing(
    date: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_date = date or datetime.date.today()
    txs = db.query(Transaction).filter(
        Transaction.date == target_date,
        Transaction.status != "ANULADO"
    ).order_by(Transaction.id.asc()).all()

    inflows_usd = sum(t.amount_usd for t in txs if t.movement_type == "INGRESO")
    outflows_usd = sum(t.amount_usd for t in txs if t.movement_type == "EGRESO")

    ventas_usd = sum(t.amount_usd for t in txs if t.movement_type == "INGRESO" and t.subtype == "VENTA_DIARIA")
    cxc_usd = sum(t.amount_usd for t in txs if t.movement_type == "INGRESO" and t.subtype == "COBRO_CXC")
    otros_in_usd = sum(t.amount_usd for t in txs if t.movement_type == "INGRESO" and t.subtype not in ["VENTA_DIARIA", "COBRO_CXC"])

    prov_usd = sum(t.amount_usd for t in txs if t.movement_type == "EGRESO" and t.subtype == "PAGO_PROVEEDOR")
    gastos_usd = sum(t.amount_usd for t in txs if t.movement_type == "EGRESO" and t.subtype == "GASTO_OPERATIVO")
    otros_out_usd = sum(t.amount_usd for t in txs if t.movement_type == "EGRESO" and t.subtype not in ["PAGO_PROVEEDOR", "GASTO_OPERATIVO"])

    by_account = {}
    for t in txs:
        acc_name = t.account.name if t.account else "Desconocida"
        if acc_name not in by_account:
            by_account[acc_name] = {"currency": t.currency, "ingresos": 0.0, "egresos": 0.0, "neto": 0.0}
        if t.movement_type == "INGRESO":
            by_account[acc_name]["ingresos"] += t.amount_original
            by_account[acc_name]["neto"] += t.amount_original
        elif t.movement_type == "EGRESO":
            by_account[acc_name]["egresos"] += t.amount_original
            by_account[acc_name]["neto"] -= t.amount_original

    # Obtener tasa BCV activa
    setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    active_bcv = float(setting.value) if setting and setting.value else 36.80

    tx_items = []
    for t in txs:
        tx_items.append({
            "id": t.id,
            "movement_type": t.movement_type,
            "subtype": t.subtype,
            "account_name": t.account.name if t.account else "",
            "category_name": t.category.name if t.category else None,
            "amount_original": round(t.amount_original, 2),
            "currency": t.currency,
            "exchange_rate": round(t.exchange_rate, 2),
            "amount_usd": round(t.amount_usd, 2),
            "reference_number": t.reference_number,
            "beneficiary": t.beneficiary,
            "description": t.description
        })

    return {
        "date": target_date.isoformat(),
        "bcv_rate": active_bcv,
        "total_inflows_usd": round(inflows_usd, 2),
        "total_outflows_usd": round(outflows_usd, 2),
        "net_day_usd": round(inflows_usd - outflows_usd, 2),
        "inflows_breakdown": {
            "ventas_usd": round(ventas_usd, 2),
            "cobros_cxc_usd": round(cxc_usd, 2),
            "otros_inflows_usd": round(otros_in_usd, 2)
        },
        "outflows_breakdown": {
            "pago_proveedores_usd": round(prov_usd, 2),
            "gastos_operativos_usd": round(gastos_usd, 2),
            "otros_outflows_usd": round(otros_out_usd, 2)
        },
        "accounts_summary": by_account,
        "count_transactions": len(txs),
        "transactions": tx_items
    }

# -------------------------------------------------------------
# Excel File Uploader & Database Reset
# -------------------------------------------------------------
@app.post("/api/import/excel")
async def import_excel_expenses(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".xltx")):
        raise HTTPException(status_code=400, detail="Formato inválido. Por favor suba un archivo Excel (.xlsx).")

    content = await file.read()
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el archivo Excel: {str(e)}")

    # Buscar hoja adecuada
    sheet_name = None
    for name in wb.sheetnames:
        low = name.lower()
        if "gasto" in low or "control" in low or "movimiento" in low or "egreso" in low:
            sheet_name = name
            break
    ws = wb[sheet_name] if sheet_name else wb.active

    # Cuentas bancarias por defecto
    acc_ves = db.query(TreasuryAccount).filter(TreasuryAccount.currency == "VES", TreasuryAccount.is_active == True).first()
    acc_usd = db.query(TreasuryAccount).filter(TreasuryAccount.currency == "USD", TreasuryAccount.is_active == True).first()
    if not acc_ves:
        acc_ves = db.query(TreasuryAccount).first()
    if not acc_usd:
        acc_usd = db.query(TreasuryAccount).first()

    # Partidas existentes
    cats = db.query(BudgetCategory).all()
    cat_map = {c.code: c.id for c in cats}

    imported_count = 0
    total_imported_usd = 0.0
    detected_month = None

    for r in range(2, ws.max_row + 1):
        raw_date = ws.cell(r, 1).value
        benef = ws.cell(r, 2).value or ""
        desc = ws.cell(r, 3).value
        cat_code = ws.cell(r, 4).value
        monto_bs = ws.cell(r, 6).value
        monto_usd = ws.cell(r, 7).value
        tasa = ws.cell(r, 8).value

        if not raw_date or (desc is None and monto_bs is None and monto_usd is None):
            continue

        if isinstance(raw_date, datetime.datetime):
            t_date = raw_date.date()
        elif isinstance(raw_date, datetime.date):
            t_date = raw_date
        else:
            try:
                t_date = datetime.datetime.strptime(str(raw_date).strip()[:10], "%Y-%m-%d").date()
            except Exception:
                try:
                    t_date = datetime.datetime.strptime(str(raw_date).strip()[:10], "%d/%m/%Y").date()
                except Exception:
                    continue

        if not detected_month:
            detected_month = f"{t_date.year:04d}-{t_date.month:02d}"

        try:
            bs_val = float(monto_bs) if monto_bs is not None else 0.0
        except Exception:
            bs_val = 0.0

        try:
            usd_val = float(monto_usd) if monto_usd is not None else 0.0
        except Exception:
            usd_val = 0.0

        try:
            rate_val = float(tasa) if tasa is not None else 756.71
        except Exception:
            rate_val = 756.71

        if bs_val <= 0 and usd_val <= 0:
            continue

        # Cuenta y moneda según monto
        if bs_val > 0:
            target_account = acc_ves
            curr = "VES"
            orig_amt = bs_val
            calc_usd = round(bs_val / rate_val, 2) if rate_val > 0 else 0.0
        else:
            target_account = acc_usd
            curr = "USD"
            orig_amt = usd_val
            calc_usd = usd_val
            rate_val = 1.0

        # Partida presupuestaria (crear al vuelo si no existe)
        cat_id = None
        try:
            code_int = int(cat_code)
            if code_int in cat_map:
                cat_id = cat_map[code_int]
            else:
                new_cat = BudgetCategory(code=code_int, name=f"Partida {code_int}", monthly_budget_usd=500.0, is_active=True)
                db.add(new_cat)
                db.flush()
                cat_map[code_int] = new_cat.id
                cat_id = new_cat.id
        except Exception:
            pass

        clean_ref = f"EXCEL-{r}"
        tx = Transaction(
            date=t_date,
            movement_type="EGRESO",
            subtype="GASTO_OPERATIVO",
            account_id=target_account.id,
            category_id=cat_id,
            amount_original=orig_amt,
            currency=curr,
            exchange_rate=rate_val,
            amount_usd=calc_usd,
            reference_number=clean_ref,
            beneficiary=str(benef).strip() if benef else "Proveedor General",
            description=str(desc).strip() if desc else "Gasto importado de archivo Excel",
            status="VERIFICADO",
            created_by_id=current_user.id,
            verified_by_id=current_user.id
        )
        db.add(tx)
        imported_count += 1
        total_imported_usd += calc_usd

    db.commit()

    return {
        "success": True,
        "imported_count": imported_count,
        "total_usd": round(total_imported_usd, 2),
        "month": detected_month or "actual",
        "message": f"Se importaron exitosamente {imported_count} movimientos por un total de ${total_imported_usd:,.2f} USD."
    }

@app.post("/api/admin/clear-transactions")
def clear_all_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["directivo"]))
):
    count = db.query(Transaction).count()
    db.query(Transaction).delete()
    db.commit()
    return {
        "success": True,
        "count_deleted": count,
        "message": f"Se han eliminado {count} movimientos. La base de datos ha quedado limpia desde cero."
    }

@app.post("/api/admin/reset-system-demo")
def reset_system_demo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["directivo"]))
):
    """
    Función para resetear la herramienta al finalizar el periodo de prueba:
    1. Elimina todos los movimientos de prueba registrados.
    2. Reinicia todos los saldos de apertura a cero ($0.00 / Bs 0.00).
    3. Conserva intactos los usuarios, categorías y cuentas configuradas.
    """
    tx_count = db.query(Transaction).count()
    db.query(Transaction).delete()

    # Resetear saldos iniciales en cuentas
    accounts = db.query(TreasuryAccount).all()
    for acc in accounts:
        acc.initial_balance = 0.0

    # Resetear saldos iniciales mensuales
    mb_list = db.query(AccountMonthlyBalance).all()
    for mb in mb_list:
        mb.initial_balance = 0.0

    db.commit()
    return {
        "success": True,
        "transactions_deleted": tx_count,
        "accounts_reset": len(accounts),
        "message": "Sistema reseteado exitosamente. Todos los movimientos de prueba fueron eliminados y las cuentas quedaron en 0.00 para iniciar operaciones reales."
    }


# -------------------------------------------------------------
# Keep-Alive & Health Check Endpoint
# -------------------------------------------------------------
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": "Todo Eléctrico Valencia - Tesorería y Flujo de Caja",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


# -------------------------------------------------------------
# Cuadre de Caja Diario & Conciliación Multicanal Endpoints
# -------------------------------------------------------------
@app.get("/api/cash-close/summary")
def get_cash_close_summary(
    date: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_date = date or datetime.date.today()
    
    # 1. Fetch transactions for this date
    txs = db.query(Transaction).filter(
        Transaction.date == target_date,
        Transaction.status != "ANULADO"
    ).all()
    
    # Check if close already exists
    existing_close = db.query(DailyCashClose).filter(DailyCashClose.date == target_date).first()
    
    # Totales por tipo y canal
    sales_fiscal_iva_usd = 0.0
    sales_notes_credit_usd = 0.0
    sales_notes_collected_usd = 0.0
    returns_total_usd = 0.0
    expenses_caja_usd = 0.0
    
    cash_usd_in = 0.0
    cash_usd_out = 0.0
    cash_ves_in = 0.0
    cash_ves_out = 0.0
    
    pos_breakdown = {"Banesco": 0.0, "Bancaribe": 0.0, "BDV": 0.0, "BNC": 0.0, "Otros": 0.0}
    pos_total_usd = 0.0
    
    bank_transfers_usd = 0.0
    cashea_usd = 0.0
    retentions_iva_usd = 0.0
    retentions_islr_usd = 0.0
    
    for t in txs:
        acc = t.account
        acc_name = acc.name.upper() if acc else ""
        
        # Ventas y Notas
        if t.movement_type == "INGRESO":
            if t.doc_type == "FACTURA_FISCAL" or t.subtype == "VENTA_DIARIA":
                sales_fiscal_iva_usd += t.amount_usd
            elif t.doc_type == "NOTA_ENTREGA":
                if t.is_credit:
                    sales_notes_credit_usd += t.amount_usd
                else:
                    sales_notes_collected_usd += t.amount_usd
            elif t.subtype == "COBRO_CXC":
                sales_notes_collected_usd += t.amount_usd
            
            # Retenciones
            if t.tax_retention_amount > 0:
                retentions_iva_usd += t.tax_retention_amount
                
            # Cobranza por canal
            if "EFECTIVO USD" in acc_name:
                cash_usd_in += t.amount_original
            elif "EFECTIVO VES" in acc_name:
                cash_ves_in += t.amount_original
            elif "CASHEA" in acc_name:
                cashea_usd += t.amount_usd
            elif "BANCO" in acc_name or "PUNTO" in acc_name or "POS" in acc_name:
                if t.pos_terminal:
                    p_term = t.pos_terminal
                    if "BANESCO" in p_term.upper():
                        pos_breakdown["Banesco"] += t.amount_usd
                    elif "BANCARIBE" in p_term.upper():
                        pos_breakdown["Bancaribe"] += t.amount_usd
                    elif "VENEZUELA" in p_term.upper() or "BDV" in p_term.upper():
                        pos_breakdown["BDV"] += t.amount_usd
                    elif "BNC" in p_term.upper():
                        pos_breakdown["BNC"] += t.amount_usd
                    else:
                        pos_breakdown["Otros"] += t.amount_usd
                    pos_total_usd += t.amount_usd
                else:
                    bank_transfers_usd += t.amount_usd
            else:
                bank_transfers_usd += t.amount_usd
                
        elif t.movement_type == "EGRESO":
            if t.subtype in ["DEVOLUCION_VENTA", "DEVOLUCION_CLIENTE"] or t.doc_type == "DEVOLUCION":
                returns_total_usd += t.amount_usd
            elif t.subtype == "GASTO_OPERATIVO":
                expenses_caja_usd += t.amount_usd
                
            if "EFECTIVO USD" in acc_name:
                cash_usd_out += t.amount_original
            elif "EFECTIVO VES" in acc_name:
                cash_ves_out += t.amount_original
                
    net_sales_usd = round(sales_fiscal_iva_usd + sales_notes_credit_usd - returns_total_usd, 2)
    total_collected_real_usd = round(cash_usd_in + (cash_ves_in / (36.80)) + pos_total_usd + bank_transfers_usd + cashea_usd, 2)
    
    return {
        "date": target_date.isoformat(),
        "is_closed": bool(existing_close),
        "existing_close": {
            "id": existing_close.id,
            "status": existing_close.status,
            "cajero_name": existing_close.cajero_name,
            "verified_by": existing_close.verified_by,
            "created_at": existing_close.created_at.strftime("%Y-%m-%d %H:%M:%S") if existing_close else "",
            "profit_sales_total_usd": existing_close.profit_sales_total_usd,
            "net_sales_usd": existing_close.net_sales_usd,
            "difference_usd": existing_close.difference_usd,
            "notes": existing_close.notes
        } if existing_close else None,
        "sales_summary": {
            "fiscal_iva_usd": round(sales_fiscal_iva_usd, 2),
            "notes_credit_usd": round(sales_notes_credit_usd, 2),
            "notes_collected_usd": round(sales_notes_collected_usd, 2),
            "returns_total_usd": round(returns_total_usd, 2),
            "net_sales_usd": net_sales_usd
        },
        "collections_summary": {
            "cash_usd_in": round(cash_usd_in, 2),
            "cash_usd_out": round(cash_usd_out, 2),
            "cash_usd_net": round(cash_usd_in - cash_usd_out, 2),
            "cash_ves_in": round(cash_ves_in, 2),
            "cash_ves_out": round(cash_ves_out, 2),
            "cash_ves_net": round(cash_ves_in - cash_ves_out, 2),
            "pos_total_usd": round(pos_total_usd, 2),
            "pos_breakdown": pos_breakdown,
            "bank_transfers_usd": round(bank_transfers_usd, 2),
            "cashea_usd": round(cashea_usd, 2),
            "retentions_iva_usd": round(retentions_iva_usd, 2),
            "retentions_islr_usd": round(retentions_islr_usd, 2),
            "expenses_caja_usd": round(expenses_caja_usd, 2),
            "total_collected_real_usd": total_collected_real_usd
        },
        "transactions_count": len(txs)
    }


@app.post("/api/cash-close")
def save_daily_cash_close(
    close_in: DailyCashCloseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(DailyCashClose).filter(DailyCashClose.date == close_in.date).first()
    if existing:
        # Update existing
        for k, v in close_in.dict().items():
            setattr(existing, k, v)
        existing.cajero_name = current_user.full_name
        db.commit()
        db.refresh(existing)
        return {"success": True, "message": f"Cuadre de caja del {close_in.date} actualizado.", "id": existing.id}
    else:
        new_close = DailyCashClose(
            **close_in.dict()
        )
        new_close.cajero_name = current_user.full_name
        db.add(new_close)
        db.commit()
        db.refresh(new_close)
        return {"success": True, "message": f"Cuadre de caja del {close_in.date} cerrado y registrado con éxito.", "id": new_close.id}


@app.get("/api/cash-close/history")
def list_cash_close_history(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    closes = db.query(DailyCashClose).order_by(DailyCashClose.date.desc()).limit(limit).all()
    res = []
    for c in closes:
        res.append({
            "id": c.id,
            "date": c.date.isoformat(),
            "cajero_name": c.cajero_name,
            "status": c.status,
            "profit_sales_total_usd": round(c.profit_sales_total_usd, 2),
            "net_sales_usd": round(c.net_sales_usd, 2),
            "cash_usd_physical": round(c.cash_usd_physical, 2),
            "cash_ves_physical": round(c.cash_ves_physical, 2),
            "total_collected_real_usd": round(c.total_collected_real_usd, 2),
            "difference_usd": round(c.difference_usd, 2),
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else ""
        })
    return res


# -------------------------------------------------------------
# Ventas Acumuladas & Panel SENIAT
# -------------------------------------------------------------
@app.get("/api/sales/accumulated")
def get_accumulated_sales(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if month:
        try:
            year, m = map(int, month.split("-"))
            start_date = datetime.date(year, m, 1)
            if m == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)
        except Exception:
            start_date = datetime.date.today().replace(day=1)
            end_date = datetime.date.today()
    else:
        start_date = datetime.date.today().replace(day=1)
        end_date = datetime.date.today()

    txs = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.status != "ANULADO"
    ).all()

    total_fiscal_iva_usd = 0.0
    total_notes_credit_usd = 0.0
    total_notes_collected_usd = 0.0
    total_retentions_iva_usd = 0.0
    total_retentions_islr_usd = 0.0
    total_returns_usd = 0.0

    for t in txs:
        if t.movement_type == "INGRESO":
            if t.doc_type == "FACTURA_FISCAL" or t.subtype == "VENTA_DIARIA":
                total_fiscal_iva_usd += t.amount_usd
            elif t.doc_type == "NOTA_ENTREGA":
                if t.is_credit:
                    total_notes_credit_usd += t.amount_usd
                else:
                    total_notes_collected_usd += t.amount_usd
            elif t.subtype == "COBRO_CXC":
                total_notes_collected_usd += t.amount_usd
            
            if t.tax_retention_amount > 0:
                total_retentions_iva_usd += t.tax_retention_amount
        elif t.movement_type == "EGRESO":
            if t.subtype in ["DEVOLUCION_VENTA", "DEVOLUCION_CLIENTE"] or t.doc_type == "DEVOLUCION":
                total_returns_usd += t.amount_usd

    return {
        "month": month or start_date.strftime("%Y-%m"),
        "period": f"{start_date.isoformat()} al {end_date.isoformat()}",
        "total_fiscal_iva_usd": round(total_fiscal_iva_usd, 2),
        "total_notes_credit_usd": round(total_notes_credit_usd, 2),
        "total_notes_collected_usd": round(total_notes_collected_usd, 2),
        "total_retentions_iva_usd": round(total_retentions_iva_usd, 2),
        "total_returns_usd": round(total_returns_usd, 2),
        "net_sales_usd": round(total_fiscal_iva_usd + total_notes_credit_usd - total_returns_usd, 2),
        "total_collected_real_usd": round(total_fiscal_iva_usd + total_notes_collected_usd - total_returns_usd, 2)
    }


# -------------------------------------------------------------
# Live Point-of-Sale (Venta en Caliente Venta por Venta) Endpoints
# -------------------------------------------------------------
@app.post("/api/sales/live")
def create_live_sale(
    sale: LiveSaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if sale.amount_original <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0.00")
        
    bcv_setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    active_bcv = float(bcv_setting.value) if (bcv_setting and bcv_setting.value) else 36.80
    
    if sale.currency == "VES":
        rate = active_bcv
        calc_usd = round(sale.amount_original / rate, 2)
    else:
        rate = 1.0
        calc_usd = round(sale.amount_original, 2)

    # If it's a Devolución
    if sale.doc_type == "DEVOLUCION":
        if not sale.account_id and not sale.is_credit:
            raise HTTPException(status_code=400, detail="Debe indicar la caja o banco de donde se realizó el reembolso.")
        
        acc_id = sale.account_id or 1
        tx = Transaction(
            date=sale.date,
            movement_type="EGRESO",
            subtype="DEVOLUCION_VENTA",
            account_id=acc_id,
            amount_original=sale.amount_original,
            currency=sale.currency,
            exchange_rate=rate,
            amount_usd=calc_usd,
            doc_type="DEVOLUCION",
            doc_number=sale.doc_number.strip(),
            client_name=sale.client_name.strip(),
            client_rif=sale.client_rif.strip() if sale.client_rif else "",
            beneficiary=sale.client_name.strip(),
            reference_number=sale.reference_number.strip() if sale.reference_number else "",
            description=sale.description.strip() or f"Devolución de mercancía ({sale.doc_number})",
            status="REGISTRADO",
            created_by_id=current_user.id
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return {"success": True, "message": f"Devolución {sale.doc_number} registrada.", "id": tx.id}

    # If it's a Credit Sale (Factura o Nota a Crédito)
    if sale.is_credit:
        # Defaults to Efectivo USD as placeholder account for credit holding
        placeholder_acc = db.query(TreasuryAccount).filter(TreasuryAccount.is_active == True).first()
        acc_id = placeholder_acc.id if placeholder_acc else 1
        
        tx = Transaction(
            date=sale.date,
            movement_type="INGRESO",
            subtype="VENTA_CREDITO_PENDIENTE",
            account_id=acc_id,
            amount_original=sale.amount_original,
            currency=sale.currency,
            exchange_rate=rate,
            amount_usd=calc_usd,
            doc_type=sale.doc_type,
            doc_number=sale.doc_number.strip(),
            client_name=sale.client_name.strip(),
            client_rif=sale.client_rif.strip() if sale.client_rif else "",
            beneficiary=sale.client_name.strip(),
            is_credit=True,
            credit_status="PENDIENTE",
            credit_original_amount_usd=calc_usd,
            credit_balance_pending_usd=calc_usd,
            reference_number=sale.reference_number.strip() if sale.reference_number else "",
            description=sale.description.strip() or f"Venta a crédito ({sale.doc_type} N° {sale.doc_number})",
            status="REGISTRADO",
            created_by_id=current_user.id
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return {"success": True, "message": f"Venta a crédito {sale.doc_type} {sale.doc_number} registrada en CxC.", "id": tx.id}

    # If it's a Cash Sale (Venta de Contado)
    if not sale.account_id:
        raise HTTPException(status_code=400, detail="Para ventas de contado debe seleccionar la caja, banco o punto de cobro.")

    acc = db.query(TreasuryAccount).filter(TreasuryAccount.id == sale.account_id).first()
    if not acc:
        raise HTTPException(status_code=400, detail="Cuenta de tesorería no encontrada.")

    # Deduct retention if applicable
    net_usd = calc_usd
    if sale.tax_retention_amount and sale.tax_retention_amount > 0:
        net_usd = max(0.0, calc_usd - sale.tax_retention_amount)

    tx = Transaction(
        date=sale.date,
        movement_type="INGRESO",
        subtype="VENTA_CALIENTE",
        account_id=acc.id,
        amount_original=sale.amount_original,
        currency=sale.currency,
        exchange_rate=rate,
        amount_usd=calc_usd,
        doc_type=sale.doc_type,
        doc_number=sale.doc_number.strip(),
        client_name=sale.client_name.strip(),
        client_rif=sale.client_rif.strip() if sale.client_rif else "",
        beneficiary=sale.client_name.strip(),
        is_credit=False,
        credit_status="PAGADO",
        tax_retention_amount=sale.tax_retention_amount or 0.0,
        tax_retention_proof=sale.tax_retention_proof.strip() if sale.tax_retention_proof else "",
        pos_terminal=sale.pos_terminal.strip() if sale.pos_terminal else "",
        pos_lot_number=sale.pos_lot_number.strip() if sale.pos_lot_number else "",
        reference_number=sale.reference_number.strip() if sale.reference_number else "",
        description=sale.description.strip() or f"Venta de contado ({sale.doc_type} N° {sale.doc_number})",
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return {"success": True, "message": f"Venta {sale.doc_type} {sale.doc_number} cobrada y registrada en caliente.", "id": tx.id}


@app.get("/api/sales/live-monitor")
def get_live_monitor(
    date: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_date = date or datetime.date.today()
    txs = db.query(Transaction).filter(
        Transaction.date == target_date,
        Transaction.status != "ANULADO"
    ).order_by(Transaction.id.desc()).all()

    bcv_setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    active_bcv = float(bcv_setting.value) if (bcv_setting and bcv_setting.value) else 36.80

    fac_contado_usd = 0.0
    fac_credito_usd = 0.0
    not_contado_usd = 0.0
    not_credito_usd = 0.0
    abonos_today_usd = 0.0
    returns_today_usd = 0.0
    expenses_today_usd = 0.0

    cash_usd_expected = 0.0
    cash_ves_expected = 0.0
    pos_banesco = 0.0
    pos_bancaribe = 0.0
    pos_bdv = 0.0
    pos_bnc = 0.0
    pago_movil_usd = 0.0
    cashea_usd = 0.0

    recent_stream = []

    for t in txs:
        acc = t.account
        acc_name = acc.name.upper() if acc else ""

        if t.movement_type == "INGRESO":
            if t.doc_type == "FACTURA_FISCAL":
                if t.is_credit:
                    fac_credito_usd += t.amount_usd
                else:
                    fac_contado_usd += t.amount_usd
            elif t.doc_type == "NOTA_ENTREGA":
                if t.is_credit:
                    not_credito_usd += t.amount_usd
                else:
                    not_contado_usd += t.amount_usd
            elif t.subtype in ["ABONO_CXC", "COBRO_CXC"]:
                abonos_today_usd += t.amount_usd

            # Fondos reales por canal
            if not t.is_credit:
                if "EFECTIVO USD" in acc_name:
                    cash_usd_expected += t.amount_original
                elif "EFECTIVO VES" in acc_name:
                    cash_ves_expected += t.amount_original
                elif "CASHEA" in acc_name:
                    cashea_usd += t.amount_usd
                elif t.pos_terminal:
                    p = t.pos_terminal.upper()
                    if "BANESCO" in p:
                        pos_banesco += t.amount_usd
                    elif "BANCARIBE" in p:
                        pos_bancaribe += t.amount_usd
                    elif "VENEZUELA" in p or "BDV" in p:
                        pos_bdv += t.amount_usd
                    else:
                        pos_bnc += t.amount_usd
                else:
                    pago_movil_usd += t.amount_usd

        elif t.movement_type == "EGRESO":
            if t.subtype in ["DEVOLUCION_VENTA", "DEVOLUCION_CLIENTE"] or t.doc_type == "DEVOLUCION":
                returns_today_usd += t.amount_usd
            elif t.subtype in ["GASTO_OPERATIVO", "VALE_CAJA"]:
                expenses_today_usd += t.amount_usd

            if "EFECTIVO USD" in acc_name:
                cash_usd_expected -= t.amount_original
            elif "EFECTIVO VES" in acc_name:
                cash_ves_expected -= t.amount_original

        recent_stream.append({
            "id": t.id,
            "created_at": t.created_at.strftime("%I:%M %p") if t.created_at else "",
            "doc_type": t.doc_type,
            "doc_number": t.doc_number or "-",
            "client_name": t.client_name or t.beneficiary or "Cliente Mostrador",
            "is_credit": t.is_credit,
            "movement_type": t.movement_type,
            "subtype": t.subtype,
            "account_name": t.account.name if t.account else "CxC",
            "amount_original": round(t.amount_original, 2),
            "currency": t.currency,
            "amount_usd": round(t.amount_usd, 2)
        })

    total_sales_today = fac_contado_usd + fac_credito_usd + not_contado_usd + not_credito_usd - returns_today_usd
    total_cash_and_pos_expected = round(
        cash_usd_expected + (cash_ves_expected / active_bcv) + pos_banesco + pos_bancaribe + pos_bdv + pos_bnc + pago_movil_usd + cashea_usd,
        2
    )

    return {
        "date": target_date.isoformat(),
        "time": datetime.datetime.now().strftime("%I:%M:%S %p"),
        "bcv_rate": active_bcv,
        "sales": {
            "fac_contado_usd": round(fac_contado_usd, 2),
            "fac_credito_usd": round(fac_credito_usd, 2),
            "not_contado_usd": round(not_contado_usd, 2),
            "not_credito_usd": round(not_credito_usd, 2),
            "abonos_today_usd": round(abonos_today_usd, 2),
            "returns_today_usd": round(returns_today_usd, 2),
            "expenses_today_usd": round(expenses_today_usd, 2),
            "total_sales_today": round(total_sales_today, 2),
            "total_contado_today": round(fac_contado_usd + not_contado_usd + abonos_today_usd - returns_today_usd - expenses_today_usd, 2),
            "total_credito_today": round(fac_credito_usd + not_credito_usd, 2)
        },
        "live_funds_expected": {
            "cash_usd_expected": round(cash_usd_expected, 2),
            "cash_ves_expected": round(cash_ves_expected, 2),
            "pos_banesco": round(pos_banesco, 2),
            "pos_bancaribe": round(pos_bancaribe, 2),
            "pos_bdv": round(pos_bdv, 2),
            "pos_bnc": round(pos_bnc, 2),
            "pos_total": round(pos_banesco + pos_bancaribe + pos_bdv + pos_bnc, 2),
            "pago_movil_usd": round(pago_movil_usd, 2),
            "cashea_usd": round(cashea_usd, 2),
            "total_funds_usd": total_cash_and_pos_expected
        },
        "recent_stream": recent_stream[:50]
    }


# -------------------------------------------------------------
# Cuentas por Cobrar (CxC) & Abonos Endpoints
# -------------------------------------------------------------
@app.get("/api/receivables")
def list_receivables(
    status_filter: Optional[str] = None, # 'PENDIENTE', 'PARCIALMENTE_PAGADO', 'PAGADO', 'TODOS'
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Transaction).filter(
        Transaction.is_credit == True,
        Transaction.status != "ANULADO"
    )

    if status_filter and status_filter != 'TODOS':
        q = q.filter(Transaction.credit_status == status_filter)
    elif not status_filter:
        q = q.filter(Transaction.credit_status.in_(["PENDIENTE", "PARCIALMENTE_PAGADO"]))

    if search:
        s = f"%{search.strip()}%"
        q = q.filter(
            (Transaction.client_name.ilike(s)) |
            (Transaction.doc_number.ilike(s)) |
            (Transaction.client_rif.ilike(s))
        )

    credits = q.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    res = []
    for c in credits:
        # Calculate abonos linked to this parent transaction
        abonos = db.query(Transaction).filter(
            Transaction.parent_transaction_id == c.id,
            Transaction.status != "ANULADO"
        ).order_by(Transaction.date.asc()).all()

        total_abonado = sum(a.amount_usd for a in abonos)
        pending = max(0.0, c.amount_usd - total_abonado)

        res.append({
            "id": c.id,
            "date": c.date.isoformat(),
            "doc_type": c.doc_type,
            "doc_number": c.doc_number,
            "client_name": c.client_name or c.beneficiary,
            "client_rif": c.client_rif or "-",
            "original_amount_usd": round(c.amount_usd, 2),
            "total_abonado_usd": round(total_abonado, 2),
            "pending_balance_usd": round(pending, 2),
            "credit_status": "PAGADO" if pending <= 0.01 else ("PARCIALMENTE_PAGADO" if total_abonado > 0 else "PENDIENTE"),
            "abonos_count": len(abonos),
            "abonos_history": [
                {
                    "id": a.id,
                    "date": a.date.isoformat(),
                    "amount_usd": round(a.amount_usd, 2),
                    "amount_orig": round(a.amount_original, 2),
                    "currency": a.currency,
                    "account_name": a.account.name if a.account else "",
                    "reference": a.reference_number
                } for a in abonos
            ]
        })
    return res


@app.post("/api/receivables/{credit_id}/abono")
def create_abono(
    credit_id: int,
    abono_in: AbonoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Row-level lock against Race Conditions
    query = db.query(Transaction).filter(Transaction.id == credit_id, Transaction.is_credit == True)
    if engine.dialect.name != 'sqlite':
        parent = query.with_for_update().first()
    else:
        parent = query.first()
    if not parent:
        raise HTTPException(status_code=404, detail="Cuenta por cobrar no encontrada.")

    account = db.query(TreasuryAccount).filter(TreasuryAccount.id == abono_in.account_id).first()
    if not account:
        raise HTTPException(status_code=400, detail="Cuenta de tesorería no encontrada.")

    bcv_setting = db.query(SystemSetting).filter(SystemSetting.key == 'bcv_rate').first()
    active_bcv = float(bcv_setting.value) if (bcv_setting and bcv_setting.value) else 36.80

    if abono_in.currency == "VES":
        rate = active_bcv
        calc_usd = round(abono_in.amount_original / rate, 2)
    else:
        rate = 1.0
        calc_usd = round(abono_in.amount_original, 2)

    # Register Abono Transaction
    tx = Transaction(
        date=abono_in.date,
        movement_type="INGRESO",
        subtype="ABONO_CXC",
        account_id=account.id,
        amount_original=abono_in.amount_original,
        currency=abono_in.currency,
        exchange_rate=rate,
        amount_usd=calc_usd,
        doc_type="ABONO_CXC",
        doc_number=f"ABONO-{parent.doc_number}",
        client_name=parent.client_name,
        client_rif=parent.client_rif,
        beneficiary=parent.client_name,
        parent_transaction_id=parent.id,
        tax_retention_amount=abono_in.tax_retention_amount or 0.0,
        tax_retention_proof=abono_in.tax_retention_proof.strip() if abono_in.tax_retention_proof else "",
        pos_terminal=abono_in.pos_terminal.strip() if abono_in.pos_terminal else "",
        pos_lot_number=abono_in.pos_lot_number.strip() if abono_in.pos_lot_number else "",
        reference_number=abono_in.reference_number.strip() if abono_in.reference_number else "",
        description=abono_in.description.strip() or f"Abono a {parent.doc_type} N° {parent.doc_number} ({parent.client_name})",
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx)
    db.flush()

    # Cálculo atómico de abonos totales registrados
    total_ab = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0.0)).filter(
        Transaction.parent_transaction_id == parent.id,
        Transaction.status != "ANULADO"
    ).scalar() or 0.0

    rem = max(0.0, parent.amount_usd - float(total_ab))
    parent.credit_balance_pending_usd = round(rem, 2)
    parent.credit_status = "PAGADO" if rem <= 0.01 else "PARCIALMENTE_PAGADO"

    record_audit(
        db,
        current_user,
        "ABONO_CXC",
        "Transaction",
        str(tx.id),
        {
            "parent_id": parent.id,
            "parent_doc": parent.doc_number,
            "abono_usd": calc_usd,
            "remaining_usd": rem,
            "client": parent.client_name
        }
    )
    db.commit()
    db.refresh(tx)

    return {
        "success": True,
        "message": f"Abono de ${calc_usd:.2f} registrado con éxito. Saldo restante: ${rem:.2f}",
        "abono_id": tx.id,
        "remaining_balance_usd": round(rem, 2),
        "status": parent.credit_status
    }


# -------------------------------------------------------------
# MULTI-BRANCH & MULTI-CASHIER ENDPOINTS (10/10 Scalability)
# -------------------------------------------------------------
class BranchCreate(BaseModel):
    code: str
    name: str
    address: Optional[str] = ""
    phone: Optional[str] = ""

class CashRegisterCreate(BaseModel):
    branch_id: int
    code: str
    name: str

@app.get("/api/branches")
def get_branches(db: Session = Depends(get_db)):
    return db.query(Branch).filter(Branch.is_active == True).all()

@app.post("/api/branches")
def create_branch(
    b_in: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["directivo", "administradora"]))
):
    existing = db.query(Branch).filter(Branch.code == b_in.code.strip().upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una sucursal con este código.")
    br = Branch(
        code=b_in.code.strip().upper(),
        name=b_in.name.strip(),
        address=b_in.address.strip() if b_in.address else "",
        phone=b_in.phone.strip() if b_in.phone else "",
        is_active=True
    )
    db.add(br)
    db.commit()
    db.refresh(br)
    record_audit(db, current_user, "CREATE_BRANCH", "Branch", str(br.id), {"code": br.code, "name": br.name})
    db.commit()
    return br

@app.get("/api/cash-registers")
def get_cash_registers(branch_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(CashRegister).filter(CashRegister.is_active == True)
    if branch_id:
        q = q.filter(CashRegister.branch_id == branch_id)
    return q.all()

@app.get("/api/audit-logs")
def get_audit_logs(
    limit: int = 50,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["directivo", "administradora"]))
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    logs = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp.isoformat(),
            "username": l.username,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": json.loads(l.details_json) if l.details_json else {},
            "ip_address": l.ip_address
        }
        for l in logs
    ]

@app.get("/api/bcv-rate/sync")
def sync_bcv_rate(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    res = resolve_effective_bcv_rate(db)
    record_audit(db, current_user, "SYNC_BCV_RATE", "SystemSetting", "tasa_bcv", {
        "rate": res["rate"],
        "policy": res.get("policy_applied", "")
    })
    db.commit()
    return {
        "rate": res["rate"],
        "synced": res.get("synced", True),
        "policy": res.get("policy_applied", ""),
        "next_rate_monday": res.get("next_rate_monday"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "message": f"Tasa BCV activa: {res['rate']:.4f} VES/USD ({res.get('policy_applied', '')})"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
