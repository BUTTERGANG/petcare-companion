from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# --- Breed ---
class BreedOut(BaseModel):
    id: int
    name: str
    size_category: Optional[str] = None
    weight_range_min: Optional[float] = None
    weight_range_max: Optional[float] = None
    lifespan_years: Optional[str] = None
    coat_type: Optional[str] = None
    shedding_level: Optional[str] = None
    grooming_freq: Optional[str] = None
    energy_level: Optional[str] = None
    trainability: Optional[str] = None
    good_with_kids: Optional[str] = None
    good_with_dogs: Optional[str] = None
    common_health_issues: Optional[str] = None
    exercise_needs_min: Optional[str] = None
    care_notes: Optional[str] = None
    diet_sensitivities: Optional[str] = None
    origin: Optional[str] = None
    temperament: Optional[str] = None
    akc_traits: Optional[dict] = None
    akc_group: Optional[str] = None
    akc_popularity_rank: Optional[int] = None
    hip_dysplasia_pct: Optional[float] = None
    median_lifespan: Optional[float] = None

    model_config = {"from_attributes": True}


# --- Dog ---
class DogCreate(BaseModel):
    name: str
    breed_id: Optional[int] = None
    dob: Optional[date] = None
    weight: Optional[float] = None
    sex: Optional[str] = None
    spayed_neutered: bool = False
    microchip_id: Optional[str] = None
    notes: Optional[str] = None


class DogUpdate(BaseModel):
    name: Optional[str] = None
    breed_id: Optional[int] = None
    dob: Optional[date] = None
    weight: Optional[float] = None
    sex: Optional[str] = None
    spayed_neutered: Optional[bool] = None
    microchip_id: Optional[str] = None
    notes: Optional[str] = None


class DogOut(BaseModel):
    id: int
    name: str
    breed_id: Optional[int] = None
    dob: Optional[date] = None
    weight: Optional[float] = None
    sex: Optional[str] = None
    spayed_neutered: bool
    microchip_id: Optional[str] = None
    photo_path: Optional[str] = None
    notes: Optional[str] = None
    breed: Optional[BreedOut] = None

    model_config = {"from_attributes": True}


class DogSummary(BaseModel):
    id: int
    name: str
    breed_name: Optional[str] = None
    age_str: Optional[str] = None
    photo_path: Optional[str] = None


# --- VetVisit ---
class VetVisitCreate(BaseModel):
    date: date
    vet_name: Optional[str] = None
    reason: str
    notes: Optional[str] = None
    cost: Optional[float] = None


class VetVisitOut(BaseModel):
    id: int
    dog_id: int
    date: date
    vet_name: Optional[str] = None
    reason: str
    notes: Optional[str] = None
    cost: Optional[float] = None
    attachment_paths: Optional[list] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Vaccination ---
class VaccinationCreate(BaseModel):
    vaccine_type: str
    date_given: date
    date_due: Optional[date] = None
    administered_by: Optional[str] = None
    reminder_enabled: bool = True
    notes: Optional[str] = None


class VaccinationOut(BaseModel):
    id: int
    dog_id: int
    vaccine_type: str
    date_given: date
    date_due: Optional[date] = None
    administered_by: Optional[str] = None
    reminder_enabled: bool
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Medication ---
class MedicationCreate(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True
    notes: Optional[str] = None


class MedicationOut(BaseModel):
    id: int
    dog_id: int
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Meal ---
class MealCreate(BaseModel):
    date: date
    meal_type: Optional[str] = None
    food_brand: Optional[str] = None
    food_name: Optional[str] = None
    amount: Optional[str] = None
    calories: Optional[float] = None
    notes: Optional[str] = None


class MealOut(BaseModel):
    id: int
    dog_id: int
    date: date
    meal_type: Optional[str] = None
    food_brand: Optional[str] = None
    food_name: Optional[str] = None
    amount: Optional[str] = None
    calories: Optional[float] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- WeightRecord ---
class WeightRecordCreate(BaseModel):
    date: date
    weight_kg: float
    notes: Optional[str] = None


class WeightRecordOut(BaseModel):
    id: int
    dog_id: int
    date: date
    weight_kg: float
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}