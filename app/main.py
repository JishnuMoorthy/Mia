from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlmodel import Session, select

from app.auth import create_token, decode_token, hash_password, verify_password
from app.db import get_session
from app.models import (
    Appointment,
    AppointmentStatus,
    Clinic,
    InventoryItem,
    Invoice,
    InvoiceStatus,
    MedicalRecord,
    MessageLog,
    MessageStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Pet,
    PetGender,
    PetParent,
    ReminderChannel,
    ReminderEntityType,
    ReminderLog,
    ReminderStatus,
    User,
    UserRole,
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def now_utc() -> dt.datetime:
    return dt.datetime.utcnow()


def password_too_long(password: str) -> bool:
    return len(password.encode("utf-8")) > 72


def count_scalar(value):
    return value[0] if isinstance(value, tuple) else value


def parse_contact_blob(value: Optional[str]) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def build_contact_blob(
    whatsapp_number: str,
    emergency_contact_name: str,
    emergency_contact_phone: str,
) -> str:
    payload = {
        "whatsapp_number": whatsapp_number or "",
        "emergency_contact_name": emergency_contact_name or "",
        "emergency_contact_phone": emergency_contact_phone or "",
    }
    return json.dumps(payload)


def get_current_user(request: Request, session: Session) -> Optional[User]:
    token = request.cookies.get("session")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = session.get(User, payload.get("sub"))
    if not user or user.deleted_at is not None or not user.is_active:
        return None
    return user


def require_user(request: Request, session: Session) -> Optional[User | RedirectResponse]:
    user = get_current_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return user


def any_clinic_exists(session: Session) -> bool:
    return session.exec(select(Clinic).where(Clinic.deleted_at.is_(None))).first() is not None


def any_user_exists(session: Session) -> bool:
    return session.exec(select(User).where(User.deleted_at.is_(None))).first() is not None


def build_appointments_context(session: Session, clinic_id: str) -> dict:
    appointments = session.exec(
        select(Appointment).where(
            Appointment.clinic_id == clinic_id, Appointment.deleted_at.is_(None)
        )
    ).all()
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == clinic_id, Pet.deleted_at.is_(None))
    ).all()
    vets = session.exec(
        select(User).where(
            User.clinic_id == clinic_id,
            User.role == UserRole.vet,
            User.deleted_at.is_(None),
        )
    ).all()
    pet_map = {p.id: p for p in pets}
    vet_map = {v.id: v for v in vets}
    return {
        "appointments": appointments,
        "pets": pets,
        "vets": vets,
        "pet_map": pet_map,
        "vet_map": vet_map,
    }


@app.get("/", response_class=HTMLResponse)
def root(request: Request, session: Session = Depends(get_session)):
    if not any_clinic_exists(session) or not any_user_exists(session):
        return RedirectResponse(url="/setup", status_code=303)
    user = get_current_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/setup", response_class=HTMLResponse)
def setup_form(request: Request, session: Session = Depends(get_session)):
    if any_clinic_exists(session) and any_user_exists(session):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("setup.html", {"request": request})


@app.post("/setup")
def setup_submit(
    request: Request,
    clinic_name: str = Form(...),
    clinic_phone: str = Form(...),
    clinic_address: str = Form(""),
    clinic_city: str = Form(""),
    clinic_state: str = Form(""),
    clinic_pincode: str = Form(""),
    admin_name: str = Form(...),
    admin_phone: str = Form(...),
    admin_email: str = Form(""),
    admin_password: str = Form(...),
    session: Session = Depends(get_session),
):
    if any_clinic_exists(session) and any_user_exists(session):
        return RedirectResponse(url="/login", status_code=303)
    if password_too_long(admin_password):
        return templates.TemplateResponse(
            "setup.html",
            {"request": request, "error": "Password must be 72 bytes or fewer."},
            status_code=400,
        )

    clinic = Clinic(
        name=clinic_name,
        phone=clinic_phone,
        address=clinic_address,
        city=clinic_city,
        state=clinic_state,
        pincode=clinic_pincode,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(clinic)
    session.commit()
    session.refresh(clinic)

    try:
        password_hash = hash_password(admin_password)
    except ValueError:
        return templates.TemplateResponse(
            "setup.html",
            {"request": request, "error": "Password must be 72 bytes or fewer."},
            status_code=400,
        )

    admin = User(
        clinic_id=clinic.id,
        name=admin_name,
        phone=admin_phone,
        email=admin_email,
        role=UserRole.admin,
        is_active=True,
        password_hash=password_hash,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(admin)
    session.commit()

    token = create_token(admin.id, admin.clinic_id, admin.role)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie("session", token, httponly=True, samesite="lax")
    return response


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login_submit(
    request: Request,
    phone: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.phone == phone, User.deleted_at.is_(None))
    ).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid credentials"}, status_code=400
        )
    token = create_token(user.id, user.clinic_id, user.role)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie("session", token, httponly=True, samesite="lax")
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response


@app.get("/reset", response_class=HTMLResponse)
def reset_form(request: Request):
    return templates.TemplateResponse("reset.html", {"request": request})


@app.post("/reset")
def reset_submit(
    request: Request,
    phone: str = Form(...),
    new_password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.phone == phone, User.deleted_at.is_(None))
    ).first()
    if not user:
        return templates.TemplateResponse(
            "reset.html", {"request": request, "error": "Phone not found"}, status_code=400
        )
    if password_too_long(new_password):
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "Password must be 72 bytes or fewer."},
            status_code=400,
        )
    try:
        user.password_hash = hash_password(new_password)
    except ValueError:
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "Password must be 72 bytes or fewer."},
            status_code=400,
        )
    user.updated_at = now_utc()
    session.add(user)
    session.commit()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect

    pets_count = count_scalar(
        session.exec(
        select(func.count()).select_from(Pet).where(
            Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None)
        )
    ).one()
    )
    today = dt.date.today()
    appointments_today = count_scalar(
        session.exec(
        select(func.count()).select_from(Appointment).where(
            Appointment.clinic_id == user.clinic_id,
            Appointment.appointment_date == today,
            Appointment.deleted_at.is_(None),
        )
    ).one()
    )
    pending_invoices = count_scalar(
        session.exec(
        select(func.count()).select_from(Invoice).where(
            Invoice.clinic_id == user.clinic_id,
            Invoice.status == InvoiceStatus.issued,
            Invoice.deleted_at.is_(None),
        )
    ).one()
    )
    low_stock_items = count_scalar(
        session.exec(
        select(func.count()).select_from(InventoryItem).where(
            InventoryItem.clinic_id == user.clinic_id,
            InventoryItem.deleted_at.is_(None),
            InventoryItem.quantity <= InventoryItem.low_stock_threshold,
        )
    ).one()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "pets_count": pets_count,
            "appointments_today": appointments_today,
            "pending_invoices": pending_invoices,
            "low_stock_items": low_stock_items,
        },
    )


# Clinics
@app.get("/clinics", response_class=HTMLResponse)
def clinics_list(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    clinics = session.exec(select(Clinic).where(Clinic.deleted_at.is_(None))).all()
    return templates.TemplateResponse(
        "clinics_list.html", {"request": request, "clinics": clinics}
    )


@app.get("/clinics/new", response_class=HTMLResponse)
def clinics_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    return templates.TemplateResponse("clinics_form.html", {"request": request})


@app.post("/clinics/new")
def clinics_create(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    pincode: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    clinic = Clinic(
        name=name,
        phone=phone,
        address=address,
        city=city,
        state=state,
        pincode=pincode,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(clinic)
    session.commit()
    return RedirectResponse(url="/clinics", status_code=303)


@app.get("/clinics/{clinic_id}/edit", response_class=HTMLResponse)
def clinics_edit(clinic_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    clinic = session.get(Clinic, clinic_id)
    if not clinic or clinic.deleted_at is not None:
        return RedirectResponse(url="/clinics", status_code=303)
    return templates.TemplateResponse(
        "clinics_form.html", {"request": request, "clinic": clinic}
    )


@app.post("/clinics/{clinic_id}/edit")
def clinics_update(
    clinic_id: str,
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    pincode: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    clinic = session.get(Clinic, clinic_id)
    if not clinic or clinic.deleted_at is not None:
        return RedirectResponse(url="/clinics", status_code=303)
    clinic.name = name
    clinic.phone = phone
    clinic.address = address
    clinic.city = city
    clinic.state = state
    clinic.pincode = pincode
    clinic.updated_at = now_utc()
    session.add(clinic)
    session.commit()
    return RedirectResponse(url="/clinics", status_code=303)


@app.post("/clinics/{clinic_id}/delete")
def clinics_delete(clinic_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    clinic = session.get(Clinic, clinic_id)
    if clinic and clinic.deleted_at is None:
        clinic.deleted_at = now_utc()
        clinic.updated_at = now_utc()
        session.add(clinic)
        session.commit()
    return RedirectResponse(url="/clinics", status_code=303)


# Users
@app.get("/users", response_class=HTMLResponse)
def users_list(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    users = session.exec(
        select(User).where(User.clinic_id == user.clinic_id, User.deleted_at.is_(None))
    ).all()
    return templates.TemplateResponse(
        "users_list.html", {"request": request, "users": users}
    )


@app.get("/users/new", response_class=HTMLResponse)
def users_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    return templates.TemplateResponse(
        "users_form.html", {"request": request, "roles": UserRole}
    )


@app.post("/users/new")
def users_create(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    role: UserRole = Form(...),
    is_active: Optional[bool] = Form(False),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    current_user = user_or_redirect
    existing = session.exec(
        select(User).where(User.phone == phone, User.deleted_at.is_(None))
    ).first()
    if existing:
        return templates.TemplateResponse(
            "users_form.html",
            {
                "request": request,
                "roles": UserRole,
                "error": "A user with this phone number already exists.",
            },
            status_code=400,
        )
    if password_too_long(password):
        return templates.TemplateResponse(
            "users_form.html",
            {
                "request": request,
                "roles": UserRole,
                "error": "Password must be 72 bytes or fewer.",
            },
            status_code=400,
        )
    try:
        password_hash = hash_password(password)
    except ValueError:
        return templates.TemplateResponse(
            "users_form.html",
            {
                "request": request,
                "roles": UserRole,
                "error": "Password must be 72 bytes or fewer.",
            },
            status_code=400,
        )
    user = User(
        clinic_id=current_user.clinic_id,
        name=name,
        phone=phone,
        email=email,
        role=role,
        is_active=bool(is_active),
        password_hash=password_hash,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return templates.TemplateResponse(
            "users_form.html",
            {
                "request": request,
                "roles": UserRole,
                "error": "A user with this phone number already exists.",
            },
            status_code=400,
        )
    return RedirectResponse(url="/users", status_code=303)


@app.get("/users/{user_id}/edit", response_class=HTMLResponse)
def users_edit(user_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = session.get(User, user_id)
    if not user or user.deleted_at is not None:
        return RedirectResponse(url="/users", status_code=303)
    return templates.TemplateResponse(
        "users_form.html", {"request": request, "user": user, "roles": UserRole}
    )


@app.post("/users/{user_id}/edit")
def users_update(
    user_id: str,
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    role: UserRole = Form(...),
    is_active: Optional[bool] = Form(False),
    password: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if not user or user.deleted_at is not None:
        return RedirectResponse(url="/users", status_code=303)
    user.name = name
    user.phone = phone
    user.email = email
    user.role = role
    user.is_active = bool(is_active)
    if password:
        if password_too_long(password):
            return templates.TemplateResponse(
                "users_form.html",
                {
                    "request": request,
                    "user": user,
                    "roles": UserRole,
                    "error": "Password must be 72 bytes or fewer.",
                },
                status_code=400,
            )
        try:
            user.password_hash = hash_password(password)
        except ValueError:
            return templates.TemplateResponse(
                "users_form.html",
                {
                    "request": request,
                    "user": user,
                    "roles": UserRole,
                    "error": "Password must be 72 bytes or fewer.",
                },
                status_code=400,
            )
    user.updated_at = now_utc()
    session.add(user)
    session.commit()
    return RedirectResponse(url="/users", status_code=303)


@app.post("/users/{user_id}/delete")
def users_delete(user_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = session.get(User, user_id)
    if user and user.deleted_at is None:
        user.deleted_at = now_utc()
        user.updated_at = now_utc()
        session.add(user)
        session.commit()
    return RedirectResponse(url="/users", status_code=303)


# Pet Parents
@app.get("/pet-parents", response_class=HTMLResponse)
def pet_parents_list(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    parents = session.exec(
        select(PetParent).where(
            PetParent.clinic_id == user.clinic_id, PetParent.deleted_at.is_(None)
        )
    ).all()
    return templates.TemplateResponse(
        "pet_parents_list.html", {"request": request, "pet_parents": parents}
    )


@app.get("/pet-parents/new", response_class=HTMLResponse)
def pet_parents_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    return templates.TemplateResponse("pet_parents_form.html", {"request": request})


@app.post("/pet-parents/new")
def pet_parents_create(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    address: str = Form(""),
    whatsapp_number: str = Form(""),
    whatsapp_same: Optional[str] = Form(None),
    emergency_contact_name: str = Form(""),
    emergency_contact_phone: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    current_user = user_or_redirect
    if whatsapp_same:
        whatsapp_number = phone
    parent = PetParent(
        clinic_id=current_user.clinic_id,
        name=name,
        phone=phone,
        email=email,
        address=address,
        govt_id_reference=build_contact_blob(
            whatsapp_number, emergency_contact_name, emergency_contact_phone
        ),
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(parent)
    session.commit()
    return RedirectResponse(url="/pet-parents", status_code=303)


@app.get("/pet-parents/{parent_id}/edit", response_class=HTMLResponse)
def pet_parents_edit(parent_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    parent = session.get(PetParent, parent_id)
    if (
        not parent
        or parent.deleted_at is not None
        or parent.clinic_id != user.clinic_id
    ):
        return RedirectResponse(url="/pet-parents", status_code=303)
    contact_blob = parse_contact_blob(parent.govt_id_reference)
    return templates.TemplateResponse(
        "pet_parents_form.html",
        {
            "request": request,
            "pet_parent": parent,
            "whatsapp_number": contact_blob.get("whatsapp_number", ""),
            "emergency_contact_name": contact_blob.get("emergency_contact_name", ""),
            "emergency_contact_phone": contact_blob.get("emergency_contact_phone", ""),
        },
    )


@app.post("/pet-parents/{parent_id}/edit")
def pet_parents_update(
    parent_id: str,
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    address: str = Form(""),
    whatsapp_number: str = Form(""),
    whatsapp_same: Optional[str] = Form(None),
    emergency_contact_name: str = Form(""),
    emergency_contact_phone: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    parent = session.get(PetParent, parent_id)
    if (
        not parent
        or parent.deleted_at is not None
        or parent.clinic_id != user.clinic_id
    ):
        return RedirectResponse(url="/pet-parents", status_code=303)
    if whatsapp_same:
        whatsapp_number = phone
    parent.name = name
    parent.phone = phone
    parent.email = email
    parent.address = address
    parent.govt_id_reference = build_contact_blob(
        whatsapp_number, emergency_contact_name, emergency_contact_phone
    )
    parent.updated_at = now_utc()
    session.add(parent)
    session.commit()
    return RedirectResponse(url="/pet-parents", status_code=303)


@app.post("/pet-parents/{parent_id}/delete")
def pet_parents_delete(parent_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    parent = session.get(PetParent, parent_id)
    if parent and parent.deleted_at is None:
        parent.deleted_at = now_utc()
        parent.updated_at = now_utc()
        session.add(parent)
        session.commit()
    return RedirectResponse(url="/pet-parents", status_code=303)


# Pets
@app.get("/pets", response_class=HTMLResponse)
def pets_list(
    request: Request,
    q: Optional[str] = None,
    species: Optional[str] = None,
    gender: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    stmt = (
        select(Pet)
        .join(PetParent, Pet.pet_parent_id == PetParent.id)
        .where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Pet.name.ilike(like))
            | (Pet.registration_number.ilike(like))
            | (PetParent.name.ilike(like))
        )
    if species:
        stmt = stmt.where(Pet.species == species)
    if gender:
        stmt = stmt.where(Pet.gender == gender)
    if sort == "name":
        stmt = stmt.order_by(Pet.name.asc())
    page = page if page and page > 0 else 1
    stmt = stmt.limit(25).offset((page - 1) * 25)
    pets = session.exec(stmt).all()
    parent_ids = {p.pet_parent_id for p in pets}
    parents = session.exec(
        select(PetParent).where(PetParent.id.in_(parent_ids))
    ).all()
    parent_map = {p.id: p for p in parents}
    return templates.TemplateResponse(
        "pets_list.html",
        {
            "request": request,
            "pets": pets,
            "parent_map": parent_map,
            "q": q or "",
            "species": species or "",
            "gender": gender or "",
            "sort": sort or "",
            "page": page,
        },
    )


@app.get("/api/pets/search")
def pets_search(q: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return JSONResponse([], status_code=401)
    user = user_or_redirect
    like = f"%{q}%"
    stmt = (
        select(Pet, PetParent)
        .join(PetParent, Pet.pet_parent_id == PetParent.id)
        .where(
            Pet.clinic_id == user.clinic_id,
            Pet.deleted_at.is_(None),
            (Pet.name.ilike(like))
            | (Pet.breed.ilike(like))
            | (Pet.registration_number.ilike(like))
            | (PetParent.name.ilike(like)),
        )
        .limit(10)
    )
    results = []
    for pet, parent in session.exec(stmt).all():
        results.append(
            {
                "id": pet.id,
                "name": pet.name,
                "breed": pet.breed,
                "owner": parent.name if parent else "",
            }
        )
    return JSONResponse(results)


@app.get("/pets/new", response_class=HTMLResponse)
def pets_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    parents = session.exec(
        select(PetParent).where(
            PetParent.clinic_id == user.clinic_id, PetParent.deleted_at.is_(None)
        )
    ).all()
    return templates.TemplateResponse(
        "pets_form.html",
        {
            "request": request,
            "parents": parents,
            "genders": PetGender,
            "species_options": ["Dog", "Cat", "Other"],
            "sterilization_options": ["Yes", "No", "Unknown"],
        },
    )


@app.post("/pets/new")
def pets_create(
    request: Request,
    pet_parent_id: str = Form(...),
    name: str = Form(...),
    species: str = Form(...),
    breed: str = Form(""),
    gender: PetGender = Form(...),
    date_of_birth: Optional[str] = Form(None),
    registration_number: str = Form(""),
    sterilization_status: str = Form(""),
    alerts: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    dob = dt.date.fromisoformat(date_of_birth) if date_of_birth else None
    pet = Pet(
        clinic_id=user.clinic_id,
        pet_parent_id=pet_parent_id,
        name=name,
        species=species,
        breed=breed,
        gender=gender,
        date_of_birth=dob,
        registration_number=registration_number,
        sterilization_status=sterilization_status or None,
        alerts=alerts or None,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(pet)
    session.commit()
    session.refresh(pet)
    return RedirectResponse(url=f"/pets/{pet.id}", status_code=303)


@app.get("/pets/{pet_id}/edit", response_class=HTMLResponse)
def pets_edit(pet_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    pet = session.get(Pet, pet_id)
    if not pet or pet.deleted_at is not None or pet.clinic_id != user.clinic_id:
        return RedirectResponse(url="/pets", status_code=303)
    parents = session.exec(
        select(PetParent).where(
            PetParent.clinic_id == user.clinic_id, PetParent.deleted_at.is_(None)
        )
    ).all()
    parent = session.get(PetParent, pet.pet_parent_id) if pet.pet_parent_id else None
    contact_blob = parse_contact_blob(parent.govt_id_reference) if parent else {}
    return templates.TemplateResponse(
        "pets_form.html",
        {
            "request": request,
            "pet": pet,
            "parents": parents,
            "genders": PetGender,
            "parent": parent,
            "contact_blob": contact_blob,
            "species_options": ["Dog", "Cat", "Other"],
            "sterilization_options": ["Yes", "No", "Unknown"],
        },
    )


@app.post("/pets/{pet_id}/edit")
def pets_update(
    pet_id: str,
    request: Request,
    pet_parent_id: str = Form(...),
    name: str = Form(...),
    species: str = Form(...),
    breed: str = Form(""),
    gender: PetGender = Form(...),
    date_of_birth: Optional[str] = Form(None),
    registration_number: str = Form(""),
    sterilization_status: str = Form(""),
    alerts: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    pet = session.get(Pet, pet_id)
    if not pet or pet.deleted_at is not None or pet.clinic_id != user.clinic_id:
        return RedirectResponse(url="/pets", status_code=303)
    pet.pet_parent_id = pet_parent_id
    pet.name = name
    pet.species = species
    pet.breed = breed
    pet.gender = gender
    pet.date_of_birth = dt.date.fromisoformat(date_of_birth) if date_of_birth else None
    pet.registration_number = registration_number
    pet.sterilization_status = sterilization_status or None
    pet.alerts = alerts or None
    pet.updated_at = now_utc()
    session.add(pet)
    session.commit()
    return RedirectResponse(url="/pets", status_code=303)


@app.post("/pets/{pet_id}/delete")
def pets_delete(pet_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    pet = session.get(Pet, pet_id)
    if pet and pet.deleted_at is None:
        pet.deleted_at = now_utc()
        pet.updated_at = now_utc()
        session.add(pet)
        session.commit()
    return RedirectResponse(url="/pets", status_code=303)

@app.get("/pets/{pet_id}", response_class=HTMLResponse)
def pets_view(pet_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    pet = session.get(Pet, pet_id)
    if not pet or pet.deleted_at is not None or pet.clinic_id != user.clinic_id:
        return RedirectResponse(url="/pets", status_code=303)
    parent = session.get(PetParent, pet.pet_parent_id) if pet.pet_parent_id else None
    contact_blob = parse_contact_blob(parent.govt_id_reference) if parent else {}

    last_visit = session.exec(
        select(Appointment)
        .where(
            Appointment.clinic_id == user.clinic_id,
            Appointment.pet_id == pet.id,
            Appointment.status == AppointmentStatus.completed,
            Appointment.deleted_at.is_(None),
        )
        .order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
    ).first()

    today = dt.date.today()
    next_appt = session.exec(
        select(Appointment)
        .where(
            Appointment.clinic_id == user.clinic_id,
            Appointment.pet_id == pet.id,
            Appointment.status == AppointmentStatus.scheduled,
            Appointment.appointment_date >= today,
            Appointment.deleted_at.is_(None),
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc())
    ).first()

    return templates.TemplateResponse(
        "pets_view.html",
        {
            "request": request,
            "pet": pet,
            "parent": parent,
            "contact_blob": contact_blob,
            "last_visit": last_visit,
            "next_appt": next_appt,
        },
    )



# Appointments
@app.get("/appointments", response_class=HTMLResponse)
def appointments_list(
    request: Request,
    pet_id: Optional[str] = None,
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    context = build_appointments_context(session, user.clinic_id)
    if pet_id:
        context["appointments"] = [
            appt for appt in context["appointments"] if appt.pet_id == pet_id
        ]
    context.update({"request": request})
    return templates.TemplateResponse("appointments_list.html", context)


@app.get("/appointments/new", response_class=HTMLResponse)
def appointments_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    ).all()
    vets = session.exec(
        select(User).where(
            User.clinic_id == user.clinic_id,
            User.role == UserRole.vet,
            User.deleted_at.is_(None),
        )
    ).all()
    return templates.TemplateResponse(
        "appointments_form.html",
        {
            "request": request,
            "pets": pets,
            "vets": vets,
            "statuses": AppointmentStatus,
        },
    )


def get_overlaps(
    session: Session,
    clinic_id: str,
    vet_id: str,
    appt_date: dt.date,
    start: dt.time,
    end: dt.time,
    exclude_id: Optional[str] = None,
) -> list[Appointment]:
    stmt = select(Appointment).where(
        Appointment.clinic_id == clinic_id,
        Appointment.vet_id == vet_id,
        Appointment.appointment_date == appt_date,
        Appointment.deleted_at.is_(None),
        Appointment.status != AppointmentStatus.cancelled,
        Appointment.status != AppointmentStatus.no_show,
    )
    if exclude_id:
        stmt = stmt.where(Appointment.id != exclude_id)
    overlaps = []
    for appt in session.exec(stmt).all():
        if start < appt.end_time and end > appt.start_time:
            overlaps.append(appt)
    return overlaps


@app.post("/appointments/new")
def appointments_create(
    request: Request,
    pet_id: str = Form(...),
    vet_id: str = Form(...),
    appointment_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    status: AppointmentStatus = Form(...),
    notes: str = Form(""),
    procedure_type: Optional[str] = Form(None),
    allow_overlap: Optional[str] = Form(None),
    confirm_override: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    appt_date = dt.date.fromisoformat(appointment_date)
    start = dt.time.fromisoformat(start_time)
    end = dt.time.fromisoformat(end_time)
    if end <= start:
        pets = session.exec(
            select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
        ).all()
        vets = session.exec(
            select(User).where(
                User.clinic_id == user.clinic_id,
                User.role == UserRole.vet,
                User.deleted_at.is_(None),
            )
        ).all()
        return templates.TemplateResponse(
            "appointments_form.html",
            {
                "request": request,
                "pets": pets,
                "vets": vets,
                "statuses": AppointmentStatus,
                "error": "End time must be after start time",
            },
            status_code=400,
        )
    overlaps = get_overlaps(session, user.clinic_id, vet_id, appt_date, start, end)
    if overlaps and not allow_overlap:
        vet = session.get(User, vet_id)
        conflicts = []
        for appt in overlaps:
            pet = session.get(Pet, appt.pet_id)
            conflicts.append(
                {
                    "vet_name": vet.name if vet else "Vet",
                    "pet_name": pet.name if pet else "Pet",
                    "start_time": appt.start_time.strftime("%H:%M"),
                    "end_time": appt.end_time.strftime("%H:%M"),
                }
            )
        return JSONResponse(
            {
                "error_code": "OVERLAP_DETECTED",
                "conflicts": conflicts,
            },
            status_code=409,
        )
    if overlaps and allow_overlap and confirm_override != "yes":
        return JSONResponse(
            {"error_code": "OVERRIDE_CONFIRMATION_REQUIRED"},
            status_code=409,
        )
    if overlaps and allow_overlap and confirm_override == "yes":
        first = overlaps[0]
        override_note = f"OVERLAP OVERRIDE: existing appt {first.start_time.strftime('%H:%M')}-{first.end_time.strftime('%H:%M')}"
        notes = f"{notes}\n{override_note}".strip()
    appointment = Appointment(
        clinic_id=user.clinic_id,
        pet_id=pet_id,
        vet_id=vet_id,
        appointment_date=appt_date,
        start_time=start,
        end_time=end,
        status=status,
        notes=notes,
        procedure_type=procedure_type or None,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(appointment)
    session.commit()
    return RedirectResponse(url="/appointments", status_code=303)


@app.get("/appointments/{appointment_id}/edit", response_class=HTMLResponse)
def appointments_edit(appointment_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    appointment = session.get(Appointment, appointment_id)
    if (
        not appointment
        or appointment.deleted_at is not None
        or appointment.clinic_id != user.clinic_id
    ):
        return RedirectResponse(url="/appointments", status_code=303)
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    ).all()
    vets = session.exec(
        select(User).where(
            User.clinic_id == user.clinic_id,
            User.role == UserRole.vet,
            User.deleted_at.is_(None),
        )
    ).all()
    return templates.TemplateResponse(
        "appointments_form.html",
        {
            "request": request,
            "appointment": appointment,
            "pets": pets,
            "vets": vets,
            "statuses": AppointmentStatus,
        },
    )


@app.post("/appointments/{appointment_id}/edit")
def appointments_update(
    appointment_id: str,
    request: Request,
    pet_id: str = Form(...),
    vet_id: str = Form(...),
    appointment_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    status: AppointmentStatus = Form(...),
    notes: str = Form(""),
    procedure_type: Optional[str] = Form(None),
    allow_overlap: Optional[str] = Form(None),
    confirm_override: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    appointment = session.get(Appointment, appointment_id)
    if (
        not appointment
        or appointment.deleted_at is not None
        or appointment.clinic_id != user.clinic_id
    ):
        return RedirectResponse(url="/appointments", status_code=303)
    appt_date = dt.date.fromisoformat(appointment_date)
    start = dt.time.fromisoformat(start_time)
    end = dt.time.fromisoformat(end_time)
    if end <= start:
        pets = session.exec(
            select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
        ).all()
        vets = session.exec(
            select(User).where(
                User.clinic_id == user.clinic_id,
                User.role == UserRole.vet,
                User.deleted_at.is_(None),
            )
        ).all()
        return templates.TemplateResponse(
            "appointments_form.html",
            {
                "request": request,
                "appointment": appointment,
                "pets": pets,
                "vets": vets,
                "statuses": AppointmentStatus,
                "error": "End time must be after start time",
            },
            status_code=400,
        )
    overlaps = get_overlaps(
        session,
        appointment.clinic_id,
        vet_id,
        appt_date,
        start,
        end,
        exclude_id=appointment.id,
    )
    if overlaps and not allow_overlap:
        vet = session.get(User, vet_id)
        conflicts = []
        for appt in overlaps:
            pet = session.get(Pet, appt.pet_id)
            conflicts.append(
                {
                    "vet_name": vet.name if vet else "Vet",
                    "pet_name": pet.name if pet else "Pet",
                    "start_time": appt.start_time.strftime("%H:%M"),
                    "end_time": appt.end_time.strftime("%H:%M"),
                }
            )
        return JSONResponse(
            {
                "error_code": "OVERLAP_DETECTED",
                "conflicts": conflicts,
            },
            status_code=409,
        )
    if overlaps and allow_overlap and confirm_override != "yes":
        return JSONResponse(
            {"error_code": "OVERRIDE_CONFIRMATION_REQUIRED"},
            status_code=409,
        )
    appointment.pet_id = pet_id
    appointment.vet_id = vet_id
    appointment.appointment_date = appt_date
    appointment.start_time = start
    appointment.end_time = end
    appointment.status = status
    appointment.procedure_type = procedure_type or None
    if overlaps and allow_overlap and confirm_override == "yes":
        first = overlaps[0]
        override_note = f"OVERLAP OVERRIDE: existing appt {first.start_time.strftime('%H:%M')}-{first.end_time.strftime('%H:%M')}"
        notes = f"{notes}\n{override_note}".strip()
    appointment.notes = notes
    appointment.updated_at = now_utc()
    session.add(appointment)
    session.commit()
    return RedirectResponse(url="/appointments", status_code=303)


@app.post("/appointments/{appointment_id}/delete")
def appointments_delete(appointment_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    appointment = session.get(Appointment, appointment_id)
    if appointment and appointment.deleted_at is None:
        appointment.deleted_at = now_utc()
        appointment.updated_at = now_utc()
        session.add(appointment)
        session.commit()
    return RedirectResponse(url="/appointments", status_code=303)


# Medical Records
@app.get("/medical-records", response_class=HTMLResponse)
def medical_records_list(
    request: Request, pet_id: Optional[str] = None, session: Session = Depends(get_session)
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    stmt = select(MedicalRecord).where(
        MedicalRecord.clinic_id == user.clinic_id, MedicalRecord.deleted_at.is_(None)
    )
    if pet_id:
        stmt = stmt.where(MedicalRecord.pet_id == pet_id)
    records = session.exec(stmt).all()
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    ).all()
    vets = session.exec(
        select(User).where(
            User.clinic_id == user.clinic_id,
            User.role == UserRole.vet,
            User.deleted_at.is_(None),
        )
    ).all()
    pet_map = {p.id: p for p in pets}
    vet_map = {v.id: v for v in vets}
    return templates.TemplateResponse(
        "medical_records_list.html",
        {
            "request": request,
            "records": records,
            "pet_map": pet_map,
            "vet_map": vet_map,
        },
    )


@app.get("/medical-records/new", response_class=HTMLResponse)
def medical_records_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    ).all()
    vets = session.exec(
        select(User).where(
            User.clinic_id == user.clinic_id,
            User.role == UserRole.vet,
            User.deleted_at.is_(None),
        )
    ).all()
    return templates.TemplateResponse(
        "medical_records_form.html",
        {"request": request, "pets": pets, "vets": vets},
    )


@app.post("/medical-records/new")
def medical_records_create(
    request: Request,
    pet_id: str = Form(...),
    vet_id: str = Form(...),
    visit_date: str = Form(...),
    symptoms: str = Form(""),
    diagnosis: str = Form(""),
    prescription: str = Form(""),
    follow_up_date: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    record = MedicalRecord(
        clinic_id=user.clinic_id,
        pet_id=pet_id,
        vet_id=vet_id,
        visit_date=dt.date.fromisoformat(visit_date),
        symptoms=symptoms,
        diagnosis=diagnosis,
        prescription=prescription,
        follow_up_date=dt.date.fromisoformat(follow_up_date) if follow_up_date else None,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(record)
    session.commit()
    return RedirectResponse(url="/medical-records", status_code=303)


@app.get("/medical-records/{record_id}/edit", response_class=HTMLResponse)
def medical_records_edit(record_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    record = session.get(MedicalRecord, record_id)
    if not record or record.deleted_at is not None or record.clinic_id != user.clinic_id:
        return RedirectResponse(url="/medical-records", status_code=303)
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    ).all()
    vets = session.exec(
        select(User).where(
            User.clinic_id == user.clinic_id,
            User.role == UserRole.vet,
            User.deleted_at.is_(None),
        )
    ).all()
    return templates.TemplateResponse(
        "medical_records_form.html",
        {"request": request, "record": record, "pets": pets, "vets": vets},
    )


@app.post("/medical-records/{record_id}/edit")
def medical_records_update(
    record_id: str,
    request: Request,
    pet_id: str = Form(...),
    vet_id: str = Form(...),
    visit_date: str = Form(...),
    symptoms: str = Form(""),
    diagnosis: str = Form(""),
    prescription: str = Form(""),
    follow_up_date: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    record = session.get(MedicalRecord, record_id)
    if not record or record.deleted_at is not None or record.clinic_id != user.clinic_id:
        return RedirectResponse(url="/medical-records", status_code=303)
    record.pet_id = pet_id
    record.vet_id = vet_id
    record.visit_date = dt.date.fromisoformat(visit_date)
    record.symptoms = symptoms
    record.diagnosis = diagnosis
    record.prescription = prescription
    record.follow_up_date = dt.date.fromisoformat(follow_up_date) if follow_up_date else None
    record.updated_at = now_utc()
    session.add(record)
    session.commit()
    return RedirectResponse(url="/medical-records", status_code=303)


@app.post("/medical-records/{record_id}/delete")
def medical_records_delete(record_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    record = session.get(MedicalRecord, record_id)
    if record and record.deleted_at is None:
        record.deleted_at = now_utc()
        record.updated_at = now_utc()
        session.add(record)
        session.commit()
    return RedirectResponse(url="/medical-records", status_code=303)


# Inventory Items
@app.get("/inventory-items", response_class=HTMLResponse)
def inventory_items_list(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    items = session.exec(
        select(InventoryItem).where(
            InventoryItem.clinic_id == user.clinic_id, InventoryItem.deleted_at.is_(None)
        )
    ).all()
    return templates.TemplateResponse(
        "inventory_items_list.html", {"request": request, "items": items}
    )


@app.get("/inventory-items/new", response_class=HTMLResponse)
def inventory_items_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    return templates.TemplateResponse("inventory_items_form.html", {"request": request})


@app.post("/inventory-items/new")
def inventory_items_create(
    request: Request,
    name: str = Form(...),
    quantity: int = Form(...),
    expiry_date: Optional[str] = Form(None),
    low_stock_threshold: int = Form(...),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    item = InventoryItem(
        clinic_id=user.clinic_id,
        name=name,
        quantity=quantity,
        expiry_date=dt.date.fromisoformat(expiry_date) if expiry_date else None,
        low_stock_threshold=low_stock_threshold,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(item)
    session.commit()
    return RedirectResponse(url="/inventory-items", status_code=303)


@app.get("/inventory-items/{item_id}/edit", response_class=HTMLResponse)
def inventory_items_edit(item_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    item = session.get(InventoryItem, item_id)
    if not item or item.deleted_at is not None or item.clinic_id != user.clinic_id:
        return RedirectResponse(url="/inventory-items", status_code=303)
    return templates.TemplateResponse(
        "inventory_items_form.html", {"request": request, "item": item}
    )


@app.post("/inventory-items/{item_id}/edit")
def inventory_items_update(
    item_id: str,
    request: Request,
    name: str = Form(...),
    quantity: int = Form(...),
    expiry_date: Optional[str] = Form(None),
    low_stock_threshold: int = Form(...),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    item = session.get(InventoryItem, item_id)
    if not item or item.deleted_at is not None or item.clinic_id != user.clinic_id:
        return RedirectResponse(url="/inventory-items", status_code=303)
    item.name = name
    item.quantity = quantity
    item.expiry_date = dt.date.fromisoformat(expiry_date) if expiry_date else None
    item.low_stock_threshold = low_stock_threshold
    item.updated_at = now_utc()
    session.add(item)
    session.commit()
    return RedirectResponse(url="/inventory-items", status_code=303)


@app.post("/inventory-items/{item_id}/delete")
def inventory_items_delete(item_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    item = session.get(InventoryItem, item_id)
    if item and item.deleted_at is None:
        item.deleted_at = now_utc()
        item.updated_at = now_utc()
        session.add(item)
        session.commit()
    return RedirectResponse(url="/inventory-items", status_code=303)


# Invoices
@app.get("/invoices", response_class=HTMLResponse)
def invoices_list(
    request: Request, pet_id: Optional[str] = None, session: Session = Depends(get_session)
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    stmt = select(Invoice).where(
        Invoice.clinic_id == user.clinic_id, Invoice.deleted_at.is_(None)
    )
    if pet_id:
        stmt = stmt.where(Invoice.pet_id == pet_id)
    invoices = session.exec(stmt).all()
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    ).all()
    pet_map = {p.id: p for p in pets}
    return templates.TemplateResponse(
        "invoices_list.html", {"request": request, "invoices": invoices, "pet_map": pet_map}
    )


@app.get("/invoices/new", response_class=HTMLResponse)
def invoices_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    ).all()
    return templates.TemplateResponse(
        "invoices_form.html",
        {"request": request, "pets": pets, "statuses": InvoiceStatus},
    )


def is_valid_invoice_status_transition(current: InvoiceStatus, new: InvoiceStatus) -> bool:
    if current == new:
        return True
    if current == InvoiceStatus.draft and new in (InvoiceStatus.issued, InvoiceStatus.cancelled):
        return True
    if current == InvoiceStatus.issued and new in (InvoiceStatus.paid, InvoiceStatus.cancelled):
        return True
    return False


@app.post("/invoices/new")
def invoices_create(
    request: Request,
    pet_id: str = Form(...),
    invoice_number: str = Form(...),
    total_amount: str = Form(...),
    gst_amount: str = Form(...),
    status: InvoiceStatus = Form(...),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    invoice = Invoice(
        clinic_id=user.clinic_id,
        pet_id=pet_id,
        invoice_number=invoice_number,
        total_amount=Decimal(total_amount),
        gst_amount=Decimal(gst_amount),
        status=status,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(invoice)
    session.commit()
    return RedirectResponse(url="/invoices", status_code=303)


@app.get("/invoices/{invoice_id}/edit", response_class=HTMLResponse)
def invoices_edit(invoice_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.deleted_at is not None or invoice.clinic_id != user.clinic_id:
        return RedirectResponse(url="/invoices", status_code=303)
    pets = session.exec(
        select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
    ).all()
    return templates.TemplateResponse(
        "invoices_form.html",
        {
            "request": request,
            "invoice": invoice,
            "pets": pets,
            "statuses": InvoiceStatus,
        },
    )


@app.post("/invoices/{invoice_id}/edit")
def invoices_update(
    invoice_id: str,
    request: Request,
    pet_id: str = Form(...),
    invoice_number: str = Form(...),
    total_amount: str = Form(...),
    gst_amount: str = Form(...),
    status: InvoiceStatus = Form(...),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.deleted_at is not None or invoice.clinic_id != user.clinic_id:
        return RedirectResponse(url="/invoices", status_code=303)
    if not is_valid_invoice_status_transition(invoice.status, status):
        pets = session.exec(
            select(Pet).where(Pet.clinic_id == user.clinic_id, Pet.deleted_at.is_(None))
        ).all()
        return templates.TemplateResponse(
            "invoices_form.html",
            {
                "request": request,
                "invoice": invoice,
                "pets": pets,
                "statuses": InvoiceStatus,
                "error": "Invalid invoice status transition",
            },
            status_code=400,
        )
    invoice.pet_id = pet_id
    invoice.invoice_number = invoice_number
    invoice.total_amount = Decimal(total_amount)
    invoice.gst_amount = Decimal(gst_amount)
    invoice.status = status
    invoice.updated_at = now_utc()
    session.add(invoice)
    session.commit()
    return RedirectResponse(url="/invoices", status_code=303)


@app.post("/invoices/{invoice_id}/delete")
def invoices_delete(invoice_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    invoice = session.get(Invoice, invoice_id)
    if invoice and invoice.deleted_at is None:
        invoice.deleted_at = now_utc()
        invoice.updated_at = now_utc()
        session.add(invoice)
        session.commit()
    return RedirectResponse(url="/invoices", status_code=303)


# Payments
@app.get("/payments", response_class=HTMLResponse)
def payments_list(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    payments = session.exec(
        select(Payment).where(Payment.clinic_id == user.clinic_id, Payment.deleted_at.is_(None))
    ).all()
    invoices = session.exec(
        select(Invoice).where(Invoice.clinic_id == user.clinic_id, Invoice.deleted_at.is_(None))
    ).all()
    invoice_map = {i.id: i for i in invoices}
    return templates.TemplateResponse(
        "payments_list.html",
        {"request": request, "payments": payments, "invoice_map": invoice_map},
    )


@app.get("/payments/new", response_class=HTMLResponse)
def payments_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    invoices = session.exec(
        select(Invoice).where(Invoice.clinic_id == user.clinic_id, Invoice.deleted_at.is_(None))
    ).all()
    return templates.TemplateResponse(
        "payments_form.html",
        {
            "request": request,
            "invoices": invoices,
            "methods": PaymentMethod,
            "statuses": PaymentStatus,
        },
    )


@app.post("/payments/new")
def payments_create(
    request: Request,
    invoice_id: str = Form(...),
    payment_method: PaymentMethod = Form(...),
    amount: str = Form(...),
    status: PaymentStatus = Form(...),
    reference_id: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    payment = Payment(
        clinic_id=user.clinic_id,
        invoice_id=invoice_id,
        payment_method=payment_method,
        amount=Decimal(amount),
        status=status,
        reference_id=reference_id,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(payment)
    session.commit()
    return RedirectResponse(url="/payments", status_code=303)


@app.get("/payments/{payment_id}/edit", response_class=HTMLResponse)
def payments_edit(payment_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    payment = session.get(Payment, payment_id)
    if not payment or payment.deleted_at is not None or payment.clinic_id != user.clinic_id:
        return RedirectResponse(url="/payments", status_code=303)
    invoices = session.exec(
        select(Invoice).where(Invoice.clinic_id == user.clinic_id, Invoice.deleted_at.is_(None))
    ).all()
    return templates.TemplateResponse(
        "payments_form.html",
        {
            "request": request,
            "payment": payment,
            "invoices": invoices,
            "methods": PaymentMethod,
            "statuses": PaymentStatus,
        },
    )


@app.post("/payments/{payment_id}/edit")
def payments_update(
    payment_id: str,
    request: Request,
    invoice_id: str = Form(...),
    payment_method: PaymentMethod = Form(...),
    amount: str = Form(...),
    status: PaymentStatus = Form(...),
    reference_id: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    payment = session.get(Payment, payment_id)
    if not payment or payment.deleted_at is not None or payment.clinic_id != user.clinic_id:
        return RedirectResponse(url="/payments", status_code=303)
    payment.invoice_id = invoice_id
    payment.payment_method = payment_method
    payment.amount = Decimal(amount)
    payment.status = status
    payment.reference_id = reference_id
    payment.updated_at = now_utc()
    session.add(payment)
    session.commit()
    return RedirectResponse(url="/payments", status_code=303)


@app.post("/payments/{payment_id}/delete")
def payments_delete(payment_id: str, request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    payment = session.get(Payment, payment_id)
    if payment and payment.deleted_at is None:
        payment.deleted_at = now_utc()
        payment.updated_at = now_utc()
        session.add(payment)
        session.commit()
    return RedirectResponse(url="/payments", status_code=303)


# Reminder Logs
@app.get("/reminder-logs", response_class=HTMLResponse)
def reminder_logs_list(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    logs = session.exec(
        select(ReminderLog).where(ReminderLog.clinic_id == user.clinic_id)
    ).all()
    return templates.TemplateResponse(
        "reminder_logs_list.html", {"request": request, "logs": logs}
    )


@app.get("/reminder-logs/new", response_class=HTMLResponse)
def reminder_logs_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    return templates.TemplateResponse(
        "reminder_logs_form.html",
        {
            "request": request,
            "entity_types": ReminderEntityType,
            "channels": ReminderChannel,
            "statuses": ReminderStatus,
        },
    )


@app.post("/reminder-logs/new")
def reminder_logs_create(
    request: Request,
    entity_type: ReminderEntityType = Form(...),
    entity_id: str = Form(...),
    channel: ReminderChannel = Form(...),
    status: ReminderStatus = Form(...),
    failure_reason: str = Form(""),
    sent_at: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    log = ReminderLog(
        clinic_id=user.clinic_id,
        entity_type=entity_type,
        entity_id=entity_id,
        channel=channel,
        status=status,
        failure_reason=failure_reason,
        sent_at=dt.datetime.fromisoformat(sent_at) if sent_at else None,
        created_at=now_utc(),
    )
    session.add(log)
    session.commit()
    return RedirectResponse(url="/reminder-logs", status_code=303)


# Message Logs
@app.get("/message-logs", response_class=HTMLResponse)
def message_logs_list(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    logs = session.exec(select(MessageLog).where(MessageLog.clinic_id == user.clinic_id)).all()
    return templates.TemplateResponse(
        "message_logs_list.html", {"request": request, "logs": logs}
    )


@app.get("/message-logs/new", response_class=HTMLResponse)
def message_logs_new(request: Request, session: Session = Depends(get_session)):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    return templates.TemplateResponse(
        "message_logs_form.html",
        {"request": request, "statuses": MessageStatus},
    )


@app.post("/message-logs/new")
def message_logs_create(
    request: Request,
    recipient_phone: str = Form(...),
    template_name: str = Form(...),
    payload: str = Form(...),
    status: MessageStatus = Form(...),
    provider_message_id: str = Form(""),
    session: Session = Depends(get_session),
):
    user_or_redirect = require_user(request, session)
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    user = user_or_redirect
    try:
        payload_json = json.loads(payload)
    except json.JSONDecodeError:
        return templates.TemplateResponse(
            "message_logs_form.html",
            {
                "request": request,
                "statuses": MessageStatus,
                "error": "Payload must be valid JSON",
            },
            status_code=400,
        )
    log = MessageLog(
        clinic_id=user.clinic_id,
        recipient_phone=recipient_phone,
        template_name=template_name,
        payload=payload_json,
        status=status,
        provider_message_id=provider_message_id,
        created_at=now_utc(),
    )
    session.add(log)
    session.commit()
    return RedirectResponse(url="/message-logs", status_code=303)
