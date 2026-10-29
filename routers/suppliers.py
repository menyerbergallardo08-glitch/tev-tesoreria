from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Supplier, User
from core.security import get_current_user, require_roles
from schemas.suppliers import SupplierCreate, SupplierUpdate
from core.audit import record_audit

router = APIRouter(prefix="/api/suppliers", tags=["Proveedores"])

@router.get("")
def list_suppliers(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Supplier)
    if not include_inactive:
        query = query.filter(Supplier.is_active == True)
    suppliers = query.order_by(Supplier.name.asc()).all()
    return [{
        "id": s.id,
        "name": s.name,
        "rif": s.rif,
        "phone": s.phone,
        "bank_details": s.bank_details,
        "is_active": s.is_active
    } for s in suppliers]

@router.post("")
def create_supplier(
    data: SupplierCreate,
    request: Request,
    current_user: User = Depends(require_roles(["administradora", "directivo", "cajera", "cajero"])),
    db: Session = Depends(get_db)
):
    clean_name = data.name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="El nombre del proveedor es obligatorio.")
    
    existing = db.query(Supplier).filter(Supplier.name.ilike(clean_name)).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            if data.rif: existing.rif = data.rif.strip()
            if data.phone: existing.phone = data.phone.strip()
            if data.bank_details: existing.bank_details = data.bank_details.strip()
            db.commit()
            db.refresh(existing)
            return {"id": existing.id, "name": existing.name, "rif": existing.rif, "phone": existing.phone}
        raise HTTPException(status_code=400, detail=f"Ya existe un proveedor registrado como '{clean_name}'.")

    s = Supplier(
        name=clean_name,
        rif=data.rif.strip() if data.rif else None,
        phone=data.phone.strip() if data.phone else None,
        bank_details=data.bank_details.strip() if data.bank_details else '',
        is_active=True
    )
    db.add(s)
    db.flush()
    ip = request.client.host if request.client else ""
    record_audit(db, current_user, 'CREATE_SUPPLIER', 'Supplier', str(s.id), {'name': s.name, 'rif': s.rif}, ip)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "name": s.name, "rif": s.rif, "phone": s.phone}

@router.put("/{supplier_id}")
def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    request: Request,
    current_user: User = Depends(require_roles(["administradora", "directivo", "cajera", "cajero"])),
    db: Session = Depends(get_db)
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")
    
    old_data = {
        'name': s.name,
        'rif': s.rif,
        'phone': s.phone,
        'bank_details': s.bank_details,
        'is_active': s.is_active
    }

    if data.name is not None and data.name.strip():
        s.name = data.name.strip()
    if data.rif is not None:
        s.rif = data.rif.strip() if data.rif else None
    if data.phone is not None:
        s.phone = data.phone.strip() if data.phone else None
    if data.bank_details is not None:
        s.bank_details = data.bank_details.strip()
    if data.is_active is not None:
        s.is_active = data.is_active

    new_data = {
        'name': s.name,
        'rif': s.rif,
        'phone': s.phone,
        'bank_details': s.bank_details,
        'is_active': s.is_active
    }

    ip = request.client.host if request.client else ""
    record_audit(db, current_user, 'UPDATE_SUPPLIER', 'Supplier', str(s.id), {
        'previous': old_data,
        'changes': new_data,
        'updated_by': current_user.username,
        'role': current_user.role
    }, ip)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "name": s.name, "rif": s.rif, "phone": s.phone, "bank_details": s.bank_details, "is_active": s.is_active}

@router.delete("/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    request: Request,
    current_user: User = Depends(require_roles(["administradora", "directivo"])),
    db: Session = Depends(get_db)
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")
    s.is_active = False
    ip = request.client.host if request.client else ""
    record_audit(db, current_user, 'DEACTIVATE_SUPPLIER', 'Supplier', str(s.id), {'name': s.name}, ip)
    db.commit()
    return {"success": True, "message": f"Proveedor '{s.name}' desactivado."}
