import os
import shutil
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .database import init_db, get_session, async_session
from .models import Breed, Dog, VetVisit, Vaccination, Medication, Meal, WeightRecord, GroomingLog, Species, Condition, Herd
from .schemas import (
    DogCreate, DogUpdate, DogOut, DogSummary, BreedOut,
    VetVisitCreate, VetVisitOut,
    VaccinationCreate, VaccinationOut,
    MedicationCreate, MedicationOut,
    MealCreate, MealOut,
    WeightRecordCreate, WeightRecordOut,
)
from .auth import (
    hash_password, verify_password, create_session_token,
    read_session_token, SESSION_COOKIE,
)
import json
import uuid

app = FastAPI(title="PetCare Companion")

# Mount static files
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# --- Helpers ---

def age_from_dob(dob: Optional[date]) -> Optional[str]:
    if not dob:
        return None
    today = date.today()
    years = today.year - dob.year
    months = today.month - dob.month
    days = today.day - dob.day
    if days < 0:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    if years > 0:
        return f"{years}y {months}m" if months else f"{years}y"
    if months > 0:
        return f"{months}m {days}d" if days else f"{months}m"
    return f"{days}d"


# --- Auth ---

PASSWORD_FILE = os.path.join(os.path.dirname(__file__), ".password")


def get_password_hash() -> Optional[str]:
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE) as f:
            return f.read().strip()
    return None


def set_password_hash(pw_hash: str):
    with open(PASSWORD_FILE, "w") as f:
        f.write(pw_hash)
    os.chmod(PASSWORD_FILE, 0o600)


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False
    return read_session_token(token) is not None


async def require_auth(request: Request):
    """FastAPI dependency: redirect to /login if not authenticated."""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


async def optional_auth(request: Request):
    """For the login page itself — if already authed, skip."""
    return None


# --- Startup: ensure breeds seeded (as before) ---

@app.on_event("startup")
async def on_startup():
    await init_db()
    async with async_session() as session:
        # Seed species (idempotent — one by one)
        for name_, slug_, icon_ in [
            ("Dog", "dog", "🐕"), ("Cat", "cat", "🐱"), ("Horse", "horse", "🐎"),
            ("Cattle", "cattle", "🐄"), ("Goat", "goat", "🐐"),
        ]:
            exists = await session.execute(select(Species).where(Species.slug == slug_))
            if not exists.scalars().first():
                session.add(Species(name=name_, slug=slug_, icon=icon_))
        await session.commit()
        # Tag legacy dog breeds with dog species_id
        from sqlalchemy import update as sa_update
        dog_sp = await session.execute(select(Species).where(Species.slug == "dog"))
        dog_species = dog_sp.scalars().first()
        if dog_species:
            await session.execute(
                sa_update(Breed).where(Breed.species_id.is_(None))
                .values(species_id=dog_species.id)
            )
            await session.commit()

        # Seed veterinary conditions KB (merge all species seed files)
        try:
            from . import conditions_seed as cs
            all_conditions = list(cs.CONDITIONS)
            import importlib
            for mod_name in ("conditions_seed_dogs", "conditions_seed_cats", "conditions_seed_large", "conditions_seed_dogs2", "conditions_seed_cats2"):
                try:
                    mod = importlib.import_module(f".{mod_name}", package="backend")
                    if hasattr(mod, "CONDITIONS"):
                        all_conditions.extend(mod.CONDITIONS)
                except ImportError:
                    pass
        except ImportError:
            all_conditions = []
        if all_conditions:
            existing_conds = await session.execute(select(sa_func.count(Condition.id)))
            if existing_conds.scalar() == 0:
                sp_map = {}
                for s_ in (await session.execute(select(Species))).scalars().all():
                    sp_map[s_.slug] = s_.id
                for c in all_conditions:
                    sid = sp_map.get(c["species"])
                    if not sid:
                        continue
                    d = {k: v for k, v in c.items() if k != "species"}
                    d["species_id"] = sid
                    session.add(Condition(**d))
                await session.commit()

        # Seed breeds (dogs) if empty
        try:
            from . import breed_seed
        except ImportError:
            breed_seed = None
        if breed_seed and hasattr(breed_seed, 'BREEDS'):
            result = await session.execute(select(sa_func.count(Breed.id)))
            count = result.scalar()
            if count == 0:
                for bdata in breed_seed.BREEDS:
                    session.add(Breed(**bdata))
                await session.commit()

                # Seed large-animal (horse/cattle/goat) breeds
        try:
            from . import large_animal_seed as las
        except ImportError:
            las = None
        if las and not hasattr(las, 'HORSE_BREEDS'):
            las = None
        if las:
            slug_to_breeds = {"horse": las.HORSE_BREEDS, "cattle": las.CATTLE_BREEDS, "goat": las.GOAT_BREEDS}
            for slug, breed_list in slug_to_breeds.items():
                sp_result2 = await session.execute(select(Species).where(Species.slug == slug))
                sp2 = sp_result2.scalars().first()
                if not sp2:
                    continue
                existing = await session.execute(
                    select(sa_func.count(Breed.id)).where(Breed.species_id == sp2.id)
                )
                if existing.scalar() == 0:
                    for bdata in breed_list:
                        bdata = dict(bdata)
                        bdata["species_id"] = sp2.id
                        session.add(Breed(**bdata))
                    await session.commit()

# Seed cat breeds if no cat breeds exist yet
        try:
            from . import cat_breed_seed
        except ImportError:
            cat_breed_seed = None
        if cat_breed_seed and hasattr(cat_breed_seed, 'BREEDS'):
            cat_sp_result = await session.execute(select(Species).where(Species.slug == "cat"))
            cat_species = cat_sp_result.scalars().first()
            existing_cats = await session.execute(
                select(sa_func.count(Breed.id)).where(Breed.species_id == (cat_species.id if cat_species else -1))
            )
            if existing_cats.scalar() == 0 and cat_species:
                # Cat breeds may collide with dog breed names (unique constraint) — skip on conflict
                for bdata in cat_breed_seed.BREEDS:
                    exists = await session.execute(select(Breed.id).where(Breed.name == bdata["name"]))
                    if exists.scalars().first():
                        continue
                    bdata = dict(bdata)
                    bdata["species_id"] = cat_species.id
                    session.add(Breed(**bdata))
                await session.commit()


# ===================== AUTH ROUTES =====================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": None})


@app.post("/login")
async def login(
    request: Request,
    password: str = Form(...),
):
    stored = get_password_hash()
    # No password set yet -> first-run setup: set it
    if stored is None:
        set_password_hash(hash_password(password))
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(SESSION_COOKIE, create_session_token(), max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax")
        return response

    if verify_password(password, stored):
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(SESSION_COOKIE, create_session_token(), max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax")
        return response

    return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Incorrect password"})


@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ===================== AUTH MIDDLEWARE =====================
# Protect everything except /login, /static, /uploads, /api/reminders

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    public_paths = ("/login", "/static", "/uploads")
    if path.startswith(public_paths) or path == "/api/reminders":
        return await call_next(request)
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return await call_next(request)


# ===================== PAGE ROUTES =====================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Dog).options(joinedload(Dog.breed)).order_by(Dog.name)
    )
    dogs = result.scalars().unique().all()

    # Upcoming reminders: vaccinations due within 30 days
    today = date.today()
    upcoming_vax = []
    for dog in dogs:
        vax_result = await session.execute(
            select(Vaccination).where(
                Vaccination.dog_id == dog.id,
                Vaccination.reminder_enabled == True,
                Vaccination.date_due.isnot(None),
            ).order_by(Vaccination.date_due)
        )
        vax_list = vax_result.scalars().all()
        for v in vax_list:
            if v.date_due and v.date_due >= today:
                days_until = (v.date_due - today).days
                if days_until <= 30:
                    upcoming_vax.append({
                        "dog_name": dog.name,
                        "dog_id": dog.id,
                        "vaccine_type": v.vaccine_type,
                        "date_due": v.date_due,
                        "days_until": days_until,
                    })

    # Active medications
    active_meds = []
    for dog in dogs:
        med_result = await session.execute(
            select(Medication).where(
                Medication.dog_id == dog.id,
                Medication.is_active == True,
            )
        )
        for m in med_result.scalars().all():
            active_meds.append({
                "dog_name": dog.name,
                "dog_id": dog.id,
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
            })

    # Recent vet visits
    recent_visits = []
    for dog in dogs:
        visit_result = await session.execute(
            select(VetVisit).where(VetVisit.dog_id == dog.id).order_by(desc(VetVisit.date)).limit(3)
        )
        for v in visit_result.scalars().all():
            recent_visits.append({
                "dog_name": dog.name,
                "dog_id": dog.id,
                "date": v.date,
                "reason": v.reason,
                "vet_name": v.vet_name,
            })
    recent_visits.sort(key=lambda x: x["date"], reverse=True)
    recent_visits = recent_visits[:5]

    dog_summaries = []
    for d in dogs:
        dog_summaries.append(DogSummary(
            id=d.id,
            name=d.name,
            breed_name=d.breed.name if d.breed else None,
            age_str=age_from_dob(d.dob),
            photo_path=d.photo_path,
        ))

    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "dogs": dog_summaries,
        "upcoming_vax": upcoming_vax,
        "active_meds": active_meds,
        "recent_visits": recent_visits,
        "today": today,
    })


# ===================== DOG ROUTES =====================

@app.get("/dogs/add", response_class=HTMLResponse)
async def add_dog_form(request: Request, species: Optional[str] = Query(None), session: AsyncSession = Depends(get_session)):
    sp_result = await session.execute(select(Species).order_by(Species.id))
    all_species = sp_result.scalars().all()
    chosen = next((s for s in all_species if s.slug == (species or "dog")), all_species[0] if all_species else None)
    result = await session.execute(
        select(Breed).where(Breed.species_id == chosen.id).order_by(Breed.name) if chosen else select(Breed).order_by(Breed.name)
    )
    breeds = result.scalars().all()
    return templates.TemplateResponse(request, "dogs/add.html", {
        "request": request, "breeds": breeds, "species_list": all_species, "current_species": chosen,
    })


@app.post("/dogs/add")
async def add_dog(
    request: Request,
    name: str = Form(...),
    species_id: Optional[int] = Form(None),
    breed_id: Optional[int] = Form(None),
    dob: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    sex: Optional[str] = Form(None),
    spayed_neutered: bool = Form(False),
    microchip_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    photo_path = None
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"dog_{int(datetime.now().timestamp())}{ext}"
        dest = os.path.join(UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            content = await photo.read()
            f.write(content)
        photo_path = f"/uploads/{filename}"

    dog_dob = None
    if dob:
        try:
            dog_dob = date.fromisoformat(dob)
        except ValueError:
            pass

    dog = Dog(
        name=name,
        species_id=species_id if species_id and species_id > 0 else None,
        breed_id=breed_id if breed_id and breed_id > 0 else None,
        dob=dog_dob,
        weight=weight,
        sex=sex,
        spayed_neutered=spayed_neutered,
        microchip_id=microchip_id or None,
        notes=notes or None,
        photo_path=photo_path,
    )
    session.add(dog)
    await session.commit()
    await session.refresh(dog)
    return RedirectResponse(url=f"/dogs/{dog.id}" + "?saved=1", status_code=303)


@app.get("/dogs/{dog_id}", response_class=HTMLResponse)
async def dog_detail(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Dog).options(joinedload(Dog.breed)).where(Dog.id == dog_id)
    )
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)

    # Timeline: all events ordered by date
    v_result = await session.execute(
        select(VetVisit).where(VetVisit.dog_id == dog_id).order_by(desc(VetVisit.date))
    )
    vacc_result = await session.execute(
        select(Vaccination).where(Vaccination.dog_id == dog_id).order_by(desc(Vaccination.date_given))
    )
    med_result = await session.execute(
        select(Medication).where(Medication.dog_id == dog_id).order_by(desc(Medication.start_date))
    )

    # Build timeline
    timeline = []
    for v in v_result.scalars().all():
        timeline.append({
            "type": "vet_visit",
            "date": v.date.isoformat(),
            "title": f"Vet Visit: {v.reason}",
            "subtitle": v.vet_name,
            "id": v.id,
            "icon": "🏥",
        })
    for v in vacc_result.scalars().all():
        timeline.append({
            "type": "vaccination",
            "date": v.date_given.isoformat(),
            "title": f"Vaccination: {v.vaccine_type}",
            "subtitle": f"Due: {v.date_due.isoformat() if v.date_due else 'N/A'}",
            "id": v.id,
            "icon": "💉",
        })
    for m in med_result.scalars().all():
        timeline.append({
            "type": "medication",
            "date": m.start_date.isoformat() if m.start_date else "",
            "title": f"Medication: {m.name}",
            "subtitle": f"{m.dosage or ''} {m.frequency or ''}",
            "id": m.id,
            "icon": "💊",
        })

    timeline.sort(key=lambda x: x["date"], reverse=True)

    return templates.TemplateResponse(request, "dogs/detail.html", {
        "request": request,
        "dog": dog,
        "age_str": age_from_dob(dog.dob),
        "timeline": timeline,
    })


@app.get("/dogs/{dog_id}/edit", response_class=HTMLResponse)
async def edit_dog_form(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Dog).options(joinedload(Dog.breed)).where(Dog.id == dog_id)
    )
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    breeds_result = await session.execute(select(Breed).order_by(Breed.name))
    breeds = breeds_result.scalars().all()
    return templates.TemplateResponse(request, "dogs/edit.html", {"request": request, "dog": dog, "breeds": breeds})


@app.post("/dogs/{dog_id}/edit")
async def edit_dog(
    dog_id: int,
    name: str = Form(...),
    breed_id: Optional[int] = Form(None),
    dob: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    sex: Optional[str] = Form(None),
    spayed_neutered: bool = Form(False),
    microchip_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)

    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"dog_{int(datetime.now().timestamp())}{ext}"
        dest = os.path.join(UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            content = await photo.read()
            f.write(content)
        dog.photo_path = f"/uploads/{filename}"

    dog.name = name
    dog.breed_id = breed_id if breed_id and breed_id > 0 else None
    if dob:
        try:
            dog.dob = date.fromisoformat(dob)
        except ValueError:
            pass
    dog.weight = weight
    dog.sex = sex
    dog.spayed_neutered = spayed_neutered
    dog.microchip_id = microchip_id or None
    dog.notes = notes or None

    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}" + "?saved=1", status_code=303)


@app.post("/dogs/{dog_id}/delete")
async def delete_dog(dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    await session.delete(dog)
    await session.commit()
    return RedirectResponse(url="/", status_code=303)


# ===================== VET VISIT ROUTES =====================

@app.get("/dogs/{dog_id}/vet-visits", response_class=HTMLResponse)
async def vet_visits_list(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    v_result = await session.execute(
        select(VetVisit).where(VetVisit.dog_id == dog_id).order_by(desc(VetVisit.date))
    )
    visits = v_result.scalars().all()
    return templates.TemplateResponse(request, "medical/vet_visits.html", {"request": request, "dog": dog, "visits": visits})


@app.get("/dogs/{dog_id}/vet-visits/add", response_class=HTMLResponse)
async def add_vet_visit_form(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "medical/add_vet_visit.html", {"request": request, "dog": dog})


@app.post("/dogs/{dog_id}/vet-visits/add")
async def add_vet_visit(
    dog_id: int,
    date_str: str = Form(...),
    vet_name: Optional[str] = Form(None),
    reason: str = Form(...),
    notes: Optional[str] = Form(None),
    cost: Optional[float] = Form(None),
    attachments: list[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    try:
        visit_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Save uploaded attachments
    attachment_paths = []
    if attachments:
        for att in attachments:
            if not att or not att.filename:
                continue
            ext = os.path.splitext(att.filename)[1][:10]
            filename = f"visit_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}{ext}"
            dest = os.path.join(UPLOAD_DIR, filename)
            with open(dest, "wb") as f:
                f.write(await att.read())
            attachment_paths.append({"path": f"/uploads/{filename}", "name": att.filename})

    visit = VetVisit(
        dog_id=dog_id,
        date=visit_date,
        vet_name=vet_name or None,
        reason=reason,
        notes=notes or None,
        cost=cost,
        attachment_paths=attachment_paths or None,
    )
    session.add(visit)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/vet-visits" + "?saved=1", status_code=303)


@app.post("/vet-visits/{visit_id}/delete")
async def delete_vet_visit(visit_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(VetVisit).where(VetVisit.id == visit_id))
    visit = result.scalars().first()
    if not visit:
        raise HTTPException(status_code=404)
    dog_id = visit.dog_id
    await session.delete(visit)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/vet-visits" + "?deleted=1", status_code=303)


# ===================== VACCINATION ROUTES =====================

@app.get("/dogs/{dog_id}/vaccinations", response_class=HTMLResponse)
async def vaccinations_list(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    v_result = await session.execute(
        select(Vaccination).where(Vaccination.dog_id == dog_id).order_by(desc(Vaccination.date_given))
    )
    vaccinations = v_result.scalars().all()
    return templates.TemplateResponse(request, "medical/vaccinations.html", {
        "request": request, "dog": dog, "vaccinations": vaccinations, "today": date.today()
    })


@app.get("/dogs/{dog_id}/vaccinations/add", response_class=HTMLResponse)
async def add_vaccination_form(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "medical/add_vaccination.html", {"request": request, "dog": dog})


@app.post("/dogs/{dog_id}/vaccinations/add")
async def add_vaccination(
    dog_id: int,
    vaccine_type: str = Form(...),
    date_given: str = Form(...),
    date_due: Optional[str] = Form(None),
    administered_by: Optional[str] = Form(None),
    reminder_enabled: bool = Form(True),
    notes: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
):
    try:
        given = date.fromisoformat(date_given)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    due = None
    if date_due:
        try:
            due = date.fromisoformat(date_due)
        except ValueError:
            pass

    vacc = Vaccination(
        dog_id=dog_id,
        vaccine_type=vaccine_type,
        date_given=given,
        date_due=due,
        administered_by=administered_by or None,
        reminder_enabled=reminder_enabled,
        notes=notes or None,
    )
    session.add(vacc)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/vaccinations" + "?saved=1", status_code=303)


@app.post("/vaccinations/{vacc_id}/delete")
async def delete_vaccination(vacc_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Vaccination).where(Vaccination.id == vacc_id))
    vacc = result.scalars().first()
    if not vacc:
        raise HTTPException(status_code=404)
    dog_id = vacc.dog_id
    await session.delete(vacc)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/vaccinations" + "?deleted=1", status_code=303)


# ===================== MEDICATION ROUTES =====================

@app.get("/dogs/{dog_id}/medications", response_class=HTMLResponse)
async def medications_list(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    m_result = await session.execute(
        select(Medication).where(Medication.dog_id == dog_id).order_by(desc(Medication.is_active), desc(Medication.start_date))
    )
    meds = m_result.scalars().all()
    return templates.TemplateResponse(request, "medical/medications.html", {"request": request, "dog": dog, "medications": meds})


@app.get("/dogs/{dog_id}/medications/add", response_class=HTMLResponse)
async def add_medication_form(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "medical/add_medication.html", {"request": request, "dog": dog})


@app.post("/dogs/{dog_id}/medications/add")
async def add_medication(
    dog_id: int,
    name: str = Form(...),
    dosage: Optional[str] = Form(None),
    frequency: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    is_active: bool = Form(True),
    notes: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
):
    s_date = None
    if start_date:
        try:
            s_date = date.fromisoformat(start_date)
        except ValueError:
            pass
    e_date = None
    if end_date:
        try:
            e_date = date.fromisoformat(end_date)
        except ValueError:
            pass

    med = Medication(
        dog_id=dog_id,
        name=name,
        dosage=dosage or None,
        frequency=frequency or None,
        start_date=s_date,
        end_date=e_date,
        is_active=is_active,
        notes=notes or None,
    )
    session.add(med)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/medications" + "?saved=1", status_code=303)


@app.post("/medications/{med_id}/toggle")
async def toggle_medication(med_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Medication).where(Medication.id == med_id))
    med = result.scalars().first()
    if not med:
        raise HTTPException(status_code=404)
    med.is_active = not med.is_active
    await session.commit()
    return RedirectResponse(url=f"/dogs/{med.dog_id}/medications" + "?saved=1", status_code=303)


@app.post("/medications/{med_id}/delete")
async def delete_medication(med_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Medication).where(Medication.id == med_id))
    med = result.scalars().first()
    if not med:
        raise HTTPException(status_code=404)
    dog_id = med.dog_id
    await session.delete(med)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/medications" + "?deleted=1", status_code=303)


# ===================== NUTRITION ROUTES =====================

@app.get("/dogs/{dog_id}/nutrition", response_class=HTMLResponse)
async def nutrition_dashboard(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    # Get meals
    meals_result = await session.execute(
        select(Meal).where(Meal.dog_id == dog_id).order_by(desc(Meal.date)).limit(50)
    )
    meals = meals_result.scalars().all()
    # Get weight records
    weight_result = await session.execute(
        select(WeightRecord).where(WeightRecord.dog_id == dog_id).order_by(WeightRecord.date)
    )
    weights = weight_result.scalars().all()
    # Build chart data (chronological)
    chart_data = {
        "labels": [w.date.isoformat() for w in weights],
        "values": [w.weight_kg for w in weights],
    }
    return templates.TemplateResponse(request, "nutrition/dashboard.html", {
        "request": request, "dog": dog, "meals": meals, "weights": list(reversed(weights)),
        "chart_data": chart_data,
    })


@app.get("/dogs/{dog_id}/meals/add", response_class=HTMLResponse)
async def add_meal_form(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "nutrition/add_meal.html", {"request": request, "dog": dog})


@app.post("/dogs/{dog_id}/meals/add")
async def add_meal(
    dog_id: int,
    date_str: str = Form(...),
    meal_type: Optional[str] = Form(None),
    food_brand: Optional[str] = Form(None),
    food_name: Optional[str] = Form(None),
    amount: Optional[str] = Form(None),
    calories: Optional[float] = Form(None),
    notes: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
):
    try:
        meal_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    meal = Meal(
        dog_id=dog_id, date=meal_date, meal_type=meal_type or None,
        food_brand=food_brand or None, food_name=food_name or None,
        amount=amount or None, calories=calories, notes=notes or None,
    )
    session.add(meal)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/nutrition" + "?saved=1", status_code=303)


@app.post("/meals/{meal_id}/delete")
async def delete_meal(meal_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Meal).where(Meal.id == meal_id))
    meal = result.scalars().first()
    if not meal:
        raise HTTPException(status_code=404)
    dog_id = meal.dog_id
    await session.delete(meal)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/nutrition" + "?deleted=1", status_code=303)


@app.get("/dogs/{dog_id}/weight/add", response_class=HTMLResponse)
async def add_weight_form(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "nutrition/add_weight.html", {"request": request, "dog": dog})


@app.post("/dogs/{dog_id}/weight/add")
async def add_weight(
    dog_id: int,
    date_str: str = Form(...),
    weight_kg: float = Form(...),
    notes: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
):
    try:
        w_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    wr = WeightRecord(dog_id=dog_id, date=w_date, weight_kg=weight_kg, notes=notes or None)
    session.add(wr)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/nutrition" + "?saved=1", status_code=303)


@app.post("/weight/{weight_id}/delete")
async def delete_weight(weight_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WeightRecord).where(WeightRecord.id == weight_id))
    wr = result.scalars().first()
    if not wr:
        raise HTTPException(status_code=404)
    dog_id = wr.dog_id
    await session.delete(wr)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/nutrition" + "?deleted=1", status_code=303)


# ===================== SYMPTOM CHECKER =====================

SYMPTOMS = [
    {"id": "vomiting_blood", "name": "Vomiting blood", "urgency": "emergency", "advice": "Seek emergency vet immediately. Blood in vomit can indicate internal bleeding, poisoning, or serious gastrointestinal issues."},
    {"id": "vomiting", "name": "Vomiting (no blood)", "urgency": "monitor", "advice": "Withhold food for 12-24 hours, offer water in small amounts. If vomiting persists beyond 24 hours or dog is lethargic, see a vet."},
    {"id": "diarrhea_blood", "name": "Diarrhea with blood", "urgency": "urgent", "advice": "Schedule a vet visit within 24 hours. Bloody diarrhea can indicate infections, parasites, or inflammatory conditions. Ensure hydration."},
    {"id": "diarrhea", "name": "Diarrhea (no blood)", "urgency": "monitor", "advice": "Withhold food for 12-24 hours. Offer boiled chicken and rice. If persists beyond 48 hours or dog seems lethargic, see a vet."},
    {"id": "not_eating", "name": "Not eating (24+ hours)", "urgency": "urgent", "advice": "Loss of appetite for 24+ hours warrants a vet visit, especially if accompanied by lethargy or other symptoms."},
    {"id": "lethargy", "name": "Lethargy / weakness", "urgency": "urgent", "advice": "Unusual lethargy or weakness should be checked by a vet within 24 hours, especially if sudden or severe."},
    {"id": "limping_sudden", "name": "Sudden limping / unable to bear weight", "urgency": "urgent", "advice": "Check for visible injuries, swelling, or foreign objects. If unable to bear weight at all, see a vet within 24 hours."},
    {"id": "limping_mild", "name": "Mild limping (still using leg)", "urgency": "monitor", "advice": "Rest your dog for 24-48 hours. If limping persists or worsens, see a vet. Check paw pads for cuts or foreign objects."},
    {"id": "seizure", "name": "Seizure", "urgency": "emergency", "advice": "Clear the area of hazards. Time the seizure. Do not put hands near mouth. If seizure lasts > 3 minutes, or multiple seizures, go to emergency vet immediately."},
    {"id": "collapsed", "name": "Collapsed / unable to stand", "urgency": "emergency", "advice": "This is a medical emergency. Transport your dog to the nearest emergency vet immediately, keeping them warm and stable."},
    {"id": "difficulty_breathing", "name": "Difficulty breathing", "urgency": "emergency", "advice": "This is a life-threatening emergency. Transport to emergency vet immediately. Keep dog calm and cool during transport."},
    {"id": "coughing", "name": "Coughing", "urgency": "monitor", "advice": "Mild coughing can be normal. If persistent (> 3 days), productive, or accompanied by lethargy or fever, see a vet."},
    {"id": "sneezing", "name": "Sneezing / nasal discharge", "urgency": "monitor", "advice": "Likely allergies or mild upper respiratory infection. If discharge becomes yellow/green or persists > 5 days, see a vet."},
    {"id": "eye_redness", "name": "Red or irritated eye", "urgency": "urgent", "advice": "Eye issues can worsen quickly. See a vet within 24 hours. Do not use human eye drops. Check for foreign objects."},
    {"id": "eye_discharge", "name": "Eye discharge / goopy eyes", "urgency": "monitor", "advice": "Wipe gently with a damp cloth. If discharge is thick, yellow/green, or persists > 2 days, see a vet."},
    {"id": "ear_scratching", "name": "Scratching ears / head shaking", "urgency": "monitor", "advice": "Likely ear infection or debris. Clean ears gently. If persists > 2 days, ears are red or smelly, see a vet."},
    {"id": "excessive_scratching", "name": "Excessive scratching / biting skin", "urgency": "monitor", "advice": "Could be allergies, fleas, or skin infection. Check for fleas. If persistent > 3 days or hair loss occurs, see a vet."},
    {"id": "hot_spot", "name": "Hot spot (moist, red, irritated skin)", "urgency": "urgent", "advice": "Hot spots can spread quickly. See a vet within 24-48 hours. Keep area clean and dry. Prevent licking with a cone."},
    {"id": "lump", "name": "New lump or bump", "urgency": "monitor", "advice": "Monitor size and texture. If it grows rapidly, changes color, or bothers the dog, see a vet. Otherwise, mention at next checkup."},
    {"id": "urinating_blood", "name": "Blood in urine", "urgency": "urgent", "advice": "Could indicate UTI, bladder stones, or other issues. See a vet within 24 hours. Ensure water intake."},
    {"id": "straining_urinate", "name": "Straining to urinate", "urgency": "emergency", "advice": "If unable to urinate at all, this is a medical emergency (possible blockage). Go to emergency vet immediately."},
    {"id": "excessive_thirst", "name": "Excessive thirst / urination", "urgency": "urgent", "advice": "Could indicate diabetes, kidney disease, or Cushing's. Schedule a vet visit within a few days with a urine sample."},
    {"id": "swollen_abdomen", "name": "Swollen / distended abdomen", "urgency": "emergency", "advice": "Could be bloat (GDV) — a life-threatening emergency. Go to emergency vet immediately. Do not wait."},
    {"id": "wound", "name": "Cut or wound", "urgency": "urgent", "advice": "Clean with warm water. Apply pressure if bleeding. If deep, won't stop bleeding, or is on the face/eye, see a vet within 24 hours."},
    {"id": "bite_wound", "name": "Animal bite wound", "urgency": "urgent", "advice": "Even small puncture wounds can become infected. See a vet within 24 hours for cleaning and possible antibiotics."},
    {"id": "snake_bite", "name": "Suspected snake bite", "urgency": "emergency", "advice": "Emergency! Keep dog calm and still. Go to emergency vet immediately. Do not cut or suck the wound. Do not apply ice."},
    {"id": "heat_stress", "name": "Heat stress / heavy panting", "urgency": "emergency", "advice": "Move to cool area immediately. Offer cool (not cold) water. Wet with cool water. If panting doesn't stop within 10 minutes or dog collapses, go to emergency vet."},
    {"id": "weight_loss", "name": "Unexplained weight loss", "urgency": "urgent", "advice": "Schedule a vet visit. Unexplained weight loss can indicate various underlying health issues."},
    {"id": "lameness", "name": "Lameness in hind legs", "urgency": "urgent", "advice": "Could indicate hip dysplasia, ACL tear, or back issues. Rest and see a vet within 24-48 hours."},
]


CAT_SYMPTOMS = [
    {"id": "cat_not_eating", "name": "Not eating (24+ hours)", "urgency": "urgent", "advice": "Cats develop hepatic lipidosis (fatty liver) after just 2-3 days without food — this is more dangerous for cats than dogs. See a vet within 24 hours."},
    {"id": "cat_vomiting", "name": "Vomiting (frequent)", "urgency": "monitor", "advice": "Occasional hairballs are normal. Frequent vomiting (>2x/day), or vomiting with lethargy, needs a vet within 24h."},
    {"id": "cat_straining_litter", "name": "Straining in litter box / not urinating", "urgency": "emergency", "advice": "MALE CATS: a blocked urethra is fatal within 24-48 hours. Even females straining need same-day vet care. This is the #1 feline emergency."},
    {"id": "cat_lethargy_hiding", "name": "Hiding + lethargy", "urgency": "urgent", "advice": "Cats hide illness instinctively. A social cat suddenly hiding is a significant sign. Vet within 24 hours."},
    {"id": "cat_breathing_open", "name": "Open-mouth breathing / panting", "urgency": "emergency", "advice": "Cats should NEVER pant like dogs except brief stress. Open-mouth breathing = respiratory or cardiac emergency. Go now."},
    {"id": "cat_drinking_lot", "name": "Drinking much more than usual", "urgency": "urgent", "advice": "Classic sign of kidney disease, diabetes, or hyperthyroidism — all common in older cats. Vet visit this week with a urine sample."},
    {"id": "cat_weight_loss", "name": "Losing weight despite eating", "urgency": "urgent", "advice": "Hyperthyroidism, diabetes, and kidney disease all present this way in cats. Bloodwork needed — vet this week."},
    {"id": "cat_overgrooming", "name": "Over-grooming / bald patches", "urgency": "monitor", "advice": "Usually stress, fleas, or allergies. Check for fleas. If skin is broken or patches spread, see a vet."},
    {"id": "cat_scratching_ears", "name": "Scratching ears / head shaking", "urgency": "monitor", "advice": "Ear mites are very common in cats. Dark coffee-ground debris = mites. Vet visit for treatment."},
    {"id": "cat_eye_watering", "name": "Watery / squinting eye", "urgency": "urgent", "advice": "Feline herpesvirus flares and corneal ulcers are common and painful. Eye issues worsen fast in cats — vet within 24h."},
    {"id": "cat_seizure", "name": "Seizure", "urgency": "emergency", "advice": "Time it, keep hands away from mouth, dim lights. Any seizure warrants emergency vet evaluation."},
    {"id": "cat_limping", "name": "Limping", "urgency": "urgent", "advice": "Check gently for wounds. Cats hide fractures well — if limping persists 12+ hours, X-rays needed."},
    {"id": "cat_drooling", "name": "Sudden drooling", "urgency": "urgent", "advice": "Often dental pain, nausea, or toxin exposure (lilies, chemicals). Check mouth carefully; vet within 24h."},
    {"id": "cat_lily_exposure", "name": "Ate any part of a lily", "urgency": "emergency", "advice": "Lilies cause fatal kidney failure in cats — even pollen grooming is lethal. EMERGENCY: aggressive IV fluids within hours save lives."},
]


HORSE_SYMPTOMS = [
    {"id": "horse_colic", "name": "Colic signs (pawing, rolling, flank-watching)", "urgency": "emergency", "advice": "Colic is the #1 horse killer. Remove food, prevent rolling, walk slowly if safe. Call vet IMMEDIATELY — colic can require surgery within hours."},
    {"id": "horse_laminitis", "name": "Laminitis signs (heat in hooves, leaning back stance)", "urgency": "emergency", "advice": "Laminitis destroys hoof tissue. Remove from grass immediately, provide soft footing, call vet. Every hour matters for permanent damage."},
    {"id": "horse_not_eating", "name": "Off feed / not interested in food", "urgency": "urgent", "advice": "Horses should eat almost constantly. Off feed often means early colic or dental pain. Check gum color and gut sounds; call vet same day."},
    {"id": "horse_no_gut_sounds", "name": "No gut sounds on left flank", "urgency": "emergency", "advice": "Silent gut precedes torsion/impaction. Emergency — this is a surgical case developing."},
    {"id": "horse_nasal_discharge", "name": "Thick nasal discharge (one or both nostrils)", "urgency": "urgent", "advice": "Could be strangles (contagious!), abscessed tooth, or pneumonia. ISOLATE the horse immediately and call vet."},
    {"id": "horse_sudden_lameness", "name": "Sudden severe lameness", "urgency": "emergency", "advice": "Could be fracture, abscess, or laminitis. Do not force movement. Call vet; hoist-poultice only if advised."},
    {"id": "horse_tying_up", "name": "Muscle cramping / dark urine after work", "urgency": "emergency", "advice": "Tying-up (azoturia) — do NOT move the horse. It damages kidneys. Call vet, keep warm, wait for guidance."},
    {"id": "horse_eye_tearful", "name": "Tearing, squinting or cloudy eye", "urgency": "emergency", "advice": "Equine eye ulcers progress to rupture in 24-48 hours. Equine eyes are true emergencies — call vet today."},
    {"id": "horse_weight_loss", "name": "Losing weight / ribby despite feeding", "urgency": "urgent", "advice": "Parasites, teeth, or metabolic disease (PPID in seniors). Vet exam + fecal count this week."},
    {"id": "horse_wounds", "name": "Deep wound / puncture", "urgency": "emergency", "advice": "Joint/tendon sheath involvement is life-threatening. If near a joint and leaking joint fluid — emergency surgery territory. Call now."},
]

CATTLE_SYMPTOMS = [
    {"id": "cattle_bloat", "name": "Bloat (swollen left flank, distended)", "urgency": "emergency", "advice": "Frothy bloat kills in hours. Stop grain/pasture access, call vet — may need stomach tube or trocar."},
    {"id": "cattle_mastitis", "name": "Hot/swollen udder or abnormal milk", "urgency": "urgent", "advice": "Mastitis spreads fast through a herd. Isolate, milk out frequently, vet for antibiotic choice."},
    {"id": "cattle_lame", "name": "Lame / reluctant to walk", "urgency": "urgent", "advice": "Foot rot or abscess common. Restrain safely and inspect hoof; vet if heat/swelling or no obvious cause."},
    {"id": "cattle_scours", "name": "Scours (diarrhea) especially in calves", "urgency": "emergency", "advice": "Calves dehydrate fatally fast. Electrolytes NOW, vet if not nursing or lethargic. Consider crypto/E.coli testing."},
    {"id": "cattle_off_feed_herd", "name": "Multiple animals off feed", "urgency": "emergency", "advice": "Group problem: toxic feed, mold, contaminated water, or infectious disease. Check feed source immediately, call vet."},
    {"id": "cattle_down", "name": "Down and cannot rise", "urgency": "emergency", "advice": "Milk fever (calcium), injury, or toxicity. Never drag. Roll to sternal, vet immediately — down cows deteriorate fast."},
    {"id": "cattle_nasal", "name": "Nasal discharge + fever in group", "urgency": "urgent", "advice": "BRD (shipping fever) complex. Treat early — delay costs lungs permanently. Vet for protocol."},
    {"id": "cattle_abortion", "name": "Abortion / stillbirth", "urgency": "urgent", "advice": "Could be brucellosis, leptospirosis, neospora — zoonotic risks. Isolate, retain fetus/placenta for necropsy, call vet."},
]

GOAT_SYMPTOMS = [
    {"id": "goat_bloat", "name": "Bloat / distended left side", "urgency": "emergency", "advice": "Same frothy bloat as cattle. No food, walking may help gas escape, emergency vet or tube."},
    {"id": "goat_scours", "name": "Scours (diarrhea)", "urgency": "urgent", "advice": "Coccidiosis in kids, parasites in adults. Fecal test needed — deworming without diagnosis breeds resistance."},
    {"id": "goat_lameness_hoof", "name": "Lame / kneeling on front knees", "urgency": "urgent", "advice": "Hoof overgrowth or foot rot. Trim hooves every 6-8 weeks; vet if infection smells foul."},
    {"id": "goat_off_feed", "name": "Off feed / separating from herd", "urgency": "urgent", "advice": "Goats hide illness but separate when sick. Check gums (anemia = barber pole worm), temp, rumen sounds."},
    {"id": "goat_pregnancy_ketosis", "name": "Pregnant doe lethargic/off feed late-term", "urgency": "emergency", "advice": "Pregnancy toxemia (ketosis) is fatal for mom AND kids. Propylene glycol orally NOW, emergency vet."},
    {"id": "goat_mastitis", "name": "Hot/hard udder in milking doe", "urgency": "urgent", "advice": "Milk out frequently, vet for antibiotics. Can become chronic/gangrenous."},
    {"id": "goat_polio", "name": "Stargazing / blind / circling", "urgency": "emergency", "advice": "Polioencephalomalacia — thiamine deficiency. Emergency thiamine injections save lives; minutes matter."},
    {"id": "goat_anemia", "name": "Pale gums / bottle jaw (swelling under jaw)", "urgency": "emergency", "advice": "Severe barber pole worm load — often fatal anemia. FAMACHA score, immediate dewormer + iron, vet."},
]


@app.get("/symptom-checker", response_class=HTMLResponse)
async def symptom_checker(request: Request, species: Optional[str] = Query(None)):
    sp = species or "dog"
    symptom_sets = {
        "dog": SYMPTOMS, "cat": CAT_SYMPTOMS,
        "horse": HORSE_SYMPTOMS, "cattle": CATTLE_SYMPTOMS, "goat": GOAT_SYMPTOMS,
    }
    items = symptom_sets.get(sp, SYMPTOMS)
    return templates.TemplateResponse(request, "symptom/checker.html", {
        "request": request, "symptoms": items, "current_species": sp,
    })


@app.get("/symptom-checker/{symptom_id}", response_class=HTMLResponse)
async def symptom_detail(request: Request, symptom_id: str):
    symptom = None
    for s in SYMPTOMS + CAT_SYMPTOMS + HORSE_SYMPTOMS + CATTLE_SYMPTOMS + GOAT_SYMPTOMS:
        if s["id"] == symptom_id:
            symptom = s
            break
    if not symptom:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "symptom/detail.html", {
        "request": request, "symptom": symptom
    })


# ===================== VET REPORT =====================

@app.get("/dogs/{dog_id}/vet-report", response_class=HTMLResponse)
async def vet_report(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Dog).options(joinedload(Dog.breed)).where(Dog.id == dog_id)
    )
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)

    v_result = await session.execute(
        select(VetVisit).where(VetVisit.dog_id == dog_id).order_by(desc(VetVisit.date))
    )
    visits = v_result.scalars().all()
    vacc_result = await session.execute(
        select(Vaccination).where(Vaccination.dog_id == dog_id).order_by(desc(Vaccination.date_given))
    )
    vaccinations = vacc_result.scalars().all()
    med_result = await session.execute(
        select(Medication).where(Medication.dog_id == dog_id).order_by(desc(Medication.is_active), desc(Medication.start_date))
    )
    meds = med_result.scalars().all()

    return templates.TemplateResponse(request, "medical/vet_report.html", {
        "request": request,
        "dog": dog,
        "age_str": age_from_dob(dog.dob),
        "visits": visits,
        "vaccinations": vaccinations,
        "medications": meds,
        "today": date.today(),
    })


# ===================== GROOMING ROUTES =====================

GROOMING_ACTIVITIES = ["bath", "nails", "ears", "teeth", "brush", "haircut"]
GROOMING_INTERVALS = {"bath": 30, "nails": 21, "ears": 14, "teeth": 7, "brush": 3, "haircut": 60}

SPECIES_GROOMING = {
    "cat": {
        "activities": ["brush", "nails", "ears", "teeth"],
        "intervals": {"brush": 3, "nails": 14, "ears": 21, "teeth": 7},
    },
    "horse": {
        "activities": ["hoof_care", "deworming", "vaccine_check", "dentist", "groom"],
        "intervals": {"hoof_care": 42, "deworming": 90, "vaccine_check": 180, "dentist": 365, "groom": 1},
    },
    "cattle": {
        "activities": ["hoof_check", "deworming", "vaccine_check"],
        "intervals": {"hoof_check": 90, "deworming": 120, "vaccine_check": 180},
    },
    "goat": {
        "activities": ["hoof_trim", "deworming", "vaccine_check", "brush"],
        "intervals": {"hoof_trim": 56, "deworming": 90, "vaccine_check": 180, "brush": 30},
    },
}


def grooming_config(species_slug):
    """Return (activities, intervals) for a species slug; dogs get the default."""
    cfg = SPECIES_GROOMING.get(species_slug or "dog")
    if cfg:
        return cfg["activities"], cfg["intervals"]
    return GROOMING_ACTIVITIES, GROOMING_INTERVALS


@app.get("/dogs/{dog_id}/grooming", response_class=HTMLResponse)
async def grooming_dashboard(request: Request, dog_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).options(joinedload(Dog.breed), joinedload(Dog.species)).where(Dog.id == dog_id))
    dog = result.scalars().first()
    if not dog:
        raise HTTPException(status_code=404)
    species_slug = dog.species.slug if dog.species else "dog"
    acts, intervals_map = grooming_config(species_slug)
    logs_result = await session.execute(
        select(GroomingLog).where(GroomingLog.dog_id == dog_id).order_by(desc(GroomingLog.date)).limit(50)
    )
    logs = logs_result.scalars().all()

    # Compute due status per activity
    today = date.today()
    activities = []
    for act in acts:
        last = next((l for l in logs if l.activity == act), None)  # logs sorted desc, so first match is latest
        last_date = last.date if last else None
        interval = intervals_map[act]
        if last_date:
            due_date = date.fromordinal(last_date.toordinal() + interval)
            days_until = (due_date - today).days
            status = "overdue" if days_until < 0 else ("due_soon" if days_until <= 3 else "ok")
        else:
            due_date = None
            days_until = None
            status = "never"
        activities.append({
            "activity": act, "last_date": last_date, "due_date": due_date,
            "days_until": days_until, "status": status, "interval": interval,
        })

    return templates.TemplateResponse(request, "grooming/dashboard.html", {
        "request": request, "dog": dog, "logs": logs, "activities": activities,
        "today": today,
    })


@app.post("/dogs/{dog_id}/grooming/log")
async def log_grooming(
    dog_id: int,
    activity: str = Form(...),
    date_str: str = Form(...),
    notes: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
):
    if activity not in GROOMING_ACTIVITIES:
        raise HTTPException(status_code=400, detail="Invalid activity")
    try:
        log_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    log = GroomingLog(dog_id=dog_id, date=log_date, activity=activity, notes=notes or None)
    session.add(log)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/grooming" + "?saved=1", status_code=303)


@app.post("/grooming/{log_id}/delete")
async def delete_grooming(log_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(GroomingLog).where(GroomingLog.id == log_id))
    log = result.scalars().first()
    if not log:
        raise HTTPException(status_code=404)
    dog_id = log.dog_id
    await session.delete(log)
    await session.commit()
    return RedirectResponse(url=f"/dogs/{dog_id}/grooming" + "?deleted=1", status_code=303)


# ===================== REMINDERS API =====================

@app.get("/api/reminders")
async def reminders_api(days: int = Query(30), session: AsyncSession = Depends(get_session)):
    """JSON endpoint for reminder checks across ALL species (used by cron / external monitors)."""
    today = date.today()
    reminders = []
    animals_result = await session.execute(select(Dog).options(joinedload(Dog.species)))
    animals = {a.id: (a.name, a.species.slug if a.species else "dog") for a in animals_result.scalars().unique().all()}

    vax_result = await session.execute(
        select(Vaccination).where(
            Vaccination.reminder_enabled == True,
            Vaccination.date_due.isnot(None),
        )
    )
    for v in vax_result.scalars().all():
        name, sp = animals.get(v.dog_id, ("?", "dog"))
        days_until = (v.date_due - today).days
        base = {"item": v.vaccine_type, "due_date": v.date_due.isoformat(),
                "days_until": days_until, "animal_id": v.dog_id, "animal_name": name, "species": sp}
        # backward-compatible keys
        base["dog_id"] = v.dog_id
        base["dog_name"] = name
        if 0 <= days_until <= days:
            reminders.append({"type": "vaccination", **base})
        elif days_until < 0:
            reminders.append({"type": "vaccination_overdue", **base})

    # Grooming overdue — species-aware intervals
    for animal_id_str, (animal_name, sp) in animals.items():
        animal_id_int = int(animal_id_str)
        acts, intervals_map = grooming_config(sp)
        logs_result = await session.execute(
            select(GroomingLog).where(GroomingLog.dog_id == animal_id_int)
        )
        last_by_act = {}
        for log in logs_result.scalars().all():
            if log.activity not in last_by_act or log.date > last_by_act[log.activity]:
                last_by_act[log.activity] = log.date
        for act in acts:
            interval = intervals_map[act]
            last = last_by_act.get(act)
            due = (last + timedelta(days=interval)) if last else None
            days_overdue = (today - due).days if due else 9999
            if days_overdue >= 0 and days_overdue <= days:
                reminders.append({
                    "type": "grooming_overdue", "dog_id": animal_id_int, "dog_name": animal_name,
                    "animal_id": animal_id_int, "animal_name": animal_name, "species": sp,
                    "item": act, "due_date": due.isoformat(), "days_until": -days_overdue,
                })

    reminders.sort(key=lambda r: r["days_until"])
    return {"generated": today.isoformat(), "count": len(reminders), "reminders": reminders}


@app.get("/feeding-calculator", response_class=HTMLResponse)
async def feeding_calculator(
    request: Request,
    weight: Optional[float] = Query(None),
    stage: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    result = None
    if weight and weight > 0:
        factor_info = next((f for f in FEEDING_FACTORS if f["id"] == stage), FEEDING_FACTORS[2])
        rer = calc_rer(weight)
        mer = calc_mer(weight, factor_info["factor"])
        cups_range = (mer / 400, mer / 300)  # typical dry food: 300–400 kcal/cup
        result = {
            "weight": weight, "stage": factor_info["label"],
            "rer": round(rer), "mer": round(mer),
            "cups_low": round(cups_range[0], 1), "cups_high": round(cups_range[1], 1),
        }
    dogs_result = await session.execute(select(Dog).order_by(Dog.name))
    dogs = dogs_result.scalars().all()
    return templates.TemplateResponse(request, "tools/feeding.html", {
        "request": request, "factors": FEEDING_FACTORS, "result": result,
        "weight": weight, "stage": stage, "dogs": dogs,
    })


# ===================== HERDS =====================

@app.get("/herds", response_class=HTMLResponse)
async def herds_list(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Herd).options(joinedload(Herd.species)).order_by(Herd.name))
    herds = result.scalars().unique().all()
    # member counts + overdue counts per herd
    data = []
    today = date.today()
    for h in herds:
        members_result = await session.execute(select(Dog).where(Dog.herd_id == h.id))
        members = members_result.scalars().all()
        data.append({"herd": h, "count": len(members), "members": members})
    return templates.TemplateResponse(request, "herds/list.html", {
        "request": request, "data": data,
    })


@app.get("/herds/new", response_class=HTMLResponse)
async def herd_new_form(request: Request, session: AsyncSession = Depends(get_session)):
    species_result = await session.execute(select(Species).order_by(Species.id))
    all_species = species_result.scalars().all()
    return templates.TemplateResponse(request, "herds/new.html", {
        "request": request, "species_list": all_species,
    })


@app.post("/herds/new")
async def herd_create(request: Request, name: str = Form(...),
                      species_id: int = Form(...),
                      notes: Optional[str] = Form(None),
                      session: AsyncSession = Depends(get_session)):
    herd = Herd(name=name, species_id=species_id, notes=notes)
    session.add(herd)
    await session.commit()
    return RedirectResponse("/herds?saved=1", status_code=303)


@app.get("/herds/{herd_id}", response_class=HTMLResponse)
async def herd_detail(request: Request, herd_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Herd).options(joinedload(Herd.species)).where(Herd.id == herd_id))
    herd = result.scalars().first()
    if not herd:
        raise HTTPException(status_code=404)
    members_result = await session.execute(select(Dog).where(Dog.herd_id == herd_id).order_by(Dog.name))
    members = members_result.scalars().all()
    unassigned_result = await session.execute(
        select(Dog).where(Dog.species_id == herd.species_id, Dog.herd_id.is_(None)).order_by(Dog.name))
    unassigned = unassigned_result.scalars().all()

    # Group-level health summary
    today = date.today()
    soon = today + timedelta(days=30)
    stats = {"members": len(members), "overdue_vaccines": 0, "due_soon": 0}
    for m in members:
        vacs_result = await session.execute(select(Vaccination).where(Vaccination.dog_id == m.id))
        for v in vacs_result.scalars().all():
            if v.date_due:
                if v.date_due < today:
                    stats["overdue_vaccines"] += 1
                elif v.date_due <= soon:
                    stats["due_soon"] += 1
    return templates.TemplateResponse(request, "herds/detail.html", {
        "request": request, "herd": herd, "members": members, "stats": stats, "unassigned": unassigned,
    })


@app.post("/herds/{herd_id}/add-member")
async def herd_add_member(herd_id: int, dog_id: int = Form(...),
                          session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Dog).where(Dog.id == dog_id))
    animal = result.scalars().first()
    if not animal:
        raise HTTPException(status_code=404)
    animal.herd_id = herd_id
    await session.commit()
    return RedirectResponse(f"/herds/{herd_id}?saved=1", status_code=303)


# ===================== KNOWLEDGE BASE =====================

@app.get("/kb/{species_slug}", response_class=HTMLResponse)
async def kb_browse(
    request: Request,
    species_slug: str,
    category: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    sp_result = await session.execute(select(Species).where(Species.slug == species_slug))
    species_obj = sp_result.scalars().first()
    if not species_obj:
        raise HTTPException(status_code=404)

    query = select(Condition).where(Condition.species_id == species_obj.id)
    if category:
        query = query.where(Condition.category == category)
    if urgency:
        query = query.where(Condition.urgency == urgency)
    if search:
        query = query.where(Condition.name.ilike(f"%{search}%"))
    # Emergency first, then urgent, then others alphabetically
    result = await session.execute(query)
    conds = result.scalars().all()
    order = {"emergency": 0, "urgent": 1, "chronic": 2, "monitor": 3}
    conds.sort(key=lambda c: (order.get(c.urgency, 4), c.name))

    categories_result = await session.execute(
        select(Condition.category).where(Condition.species_id == species_obj.id).distinct()
    )
    categories = sorted([c for c in categories_result.scalars().all() if c])

    return templates.TemplateResponse(request, "kb/browse.html", {
        "request": request, "species": species_obj, "conditions": conds,
        "categories": categories, "current_category": category,
        "current_urgency": urgency, "search": search,
    })


@app.get("/kb/{species_slug}/{slug}", response_class=HTMLResponse)
async def kb_detail(request: Request, species_slug: str, slug: str,
                    session: AsyncSession = Depends(get_session)):
    sp_result = await session.execute(select(Species).where(Species.slug == species_slug))
    species_obj = sp_result.scalars().first()
    if not species_obj:
        raise HTTPException(status_code=404)
    result = await session.execute(
        select(Condition).where(Condition.slug == slug, Condition.species_id == species_obj.id)
    )
    condition = result.scalars().first()
    if not condition:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "kb/detail.html", {
        "request": request, "species": species_obj, "condition": condition,
    })


@app.get("/toxic-foods", response_class=HTMLResponse)
async def toxic_foods(request: Request):
    danger = [f for f in TOXIC_FOODS if f["severity"] == "danger"]
    caution = [f for f in TOXIC_FOODS if f["severity"] == "caution"]
    return templates.TemplateResponse(request, "tools/toxic_foods.html", {
        "request": request, "danger": danger, "caution": caution,
    })


# ===================== BREED ROUTES =====================

@app.get("/breeds", response_class=HTMLResponse)
async def breeds_list(
    request: Request,
    search: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    species: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    query = select(Breed).order_by(Breed.name)
    if species:
        sp_result = await session.execute(select(Species).where(Species.slug == species))
        sp = sp_result.scalars().first()
        if sp:
            query = query.where(Breed.species_id == sp.id)
    if search:
        query = query.where(Breed.name.ilike(f"%{search}%"))
    if size:
        query = query.where(Breed.size_category == size)
    result = await session.execute(query)
    breeds = result.scalars().all()
    return templates.TemplateResponse(request, "breeds/list.html", {
        "request": request,
        "breeds": breeds,
        "search": search,
        "size": size,
    })


@app.get("/breeds/{breed_id}", response_class=HTMLResponse)
async def breed_detail(request: Request, breed_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Breed).where(Breed.id == breed_id))
    breed = result.scalars().first()
    if not breed:
        raise HTTPException(status_code=404)
    # Find dogs of this breed
    dogs_result = await session.execute(select(Dog).where(Dog.breed_id == breed_id))
    dogs = dogs_result.scalars().all()
    return templates.TemplateResponse(request, "breeds/detail.html", {
        "request": request,
        "breed": breed,
        "dogs": dogs,
    })