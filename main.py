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
from models import User, BudgetCategory, TreasuryAccount, Transaction, AccountMonthlyBalance
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_roles,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Todo Eléctrico Valencia - Sistema de Tesorería, Gastos y Flujo de Caja",
    version="1.2.0"
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    categories = db.query(BudgetCategory).filter(BudgetCategory.is_active == True).order_by(BudgetCategory.code).all()
    
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

    account = db.query(TreasuryAccount).filter(TreasuryAccount.id == tx_in.account_id).first()
    if not account:
        raise HTTPException(status_code=400, detail="La cuenta de tesorería seleccionada no existe.")

    # Control de duplicados por referencia bancaria (excepto cierres Z o vacíos)
    if tx_in.reference_number and len(tx_in.reference_number.strip()) > 3 and tx_in.subtype != "VENTA_DIARIA":
        ref = tx_in.reference_number.strip()
        dup = db.query(Transaction).filter(
            Transaction.reference_number == ref,
            Transaction.account_id == account.id,
            Transaction.status != "ANULADO"
        ).first()
        if dup:
            raise HTTPException(
                status_code=400,
                detail=f"¡Alerta de Duplicado! La referencia bancaria '{ref}' ya fue registrada previamente el {dup.date} por ${dup.amount_usd:.2f}."
            )

    rate = tx_in.exchange_rate if tx_in.exchange_rate > 0 else 1.0
    if tx_in.currency == "VES":
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
        status="REGISTRADO",
        created_by_id=current_user.id
    )
    db.add(tx)
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
    ).all()

    inflows_usd = sum(t.amount_usd for t in txs if t.movement_type == "INGRESO")
    outflows_usd = sum(t.amount_usd for t in txs if t.movement_type == "EGRESO")

    by_account = {}
    for t in txs:
        acc_name = t.account.name if t.account else "Desconocida"
        if acc_name not in by_account:
            by_account[acc_name] = {"currency": t.currency, "ingresos": 0.0, "egresos": 0.0}
        if t.movement_type == "INGRESO":
            by_account[acc_name]["ingresos"] += t.amount_original
        elif t.movement_type == "EGRESO":
            by_account[acc_name]["egresos"] += t.amount_original

    return {
        "date": target_date.isoformat(),
        "total_inflows_usd": round(inflows_usd, 2),
        "total_outflows_usd": round(outflows_usd, 2),
        "net_day_usd": round(inflows_usd - outflows_usd, 2),
        "accounts_summary": by_account,
        "count_transactions": len(txs)
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
    current_user: User = Depends(require_roles(["administradora", "directivo"]))
):
    count = db.query(Transaction).count()
    db.query(Transaction).delete()
    db.commit()
    return {
        "success": True,
        "count_deleted": count,
        "message": f"Se han eliminado {count} movimientos. La base de datos ha quedado limpia desde cero."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
