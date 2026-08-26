from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, Date, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Species(Base):
    __tablename__ = "species"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # Dog, Cat, ...
    slug = Column(String(50), unique=True, nullable=False)  # dog, cat
    icon = Column(String(10), nullable=True)  # emoji
    has_breeds = Column(Boolean, default=True)

    breeds = relationship("Breed", back_populates="species")


class Breed(Base):
    __tablename__ = "breeds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=True)  # nullable = legacy dog data
    name = Column(String(100), unique=True, nullable=False, index=True)
    size_category = Column(String(20), nullable=True)  # toy, small, medium, large, giant
    weight_range_min = Column(Float, nullable=True)  # kg
    weight_range_max = Column(Float, nullable=True)  # kg
    lifespan_years = Column(String(30), nullable=True)
    coat_type = Column(String(100), nullable=True)
    shedding_level = Column(String(30), nullable=True)  # low, moderate, high
    grooming_freq = Column(String(50), nullable=True)
    energy_level = Column(String(30), nullable=True)  # low, moderate, high, very high
    trainability = Column(String(30), nullable=True)  # easy, moderate, challenging
    good_with_kids = Column(String(30), nullable=True)
    good_with_dogs = Column(String(30), nullable=True)
    common_health_issues = Column(Text, nullable=True)
    exercise_needs_min = Column(String(50), nullable=True)
    care_notes = Column(Text, nullable=True)
    diet_sensitivities = Column(Text, nullable=True)
    origin = Column(String(100), nullable=True)
    temperament = Column(Text, nullable=True)
    akc_traits = Column(JSON, nullable=True)  # AKC 1-5 trait scorecard
    akc_group = Column(String(50), nullable=True)  # e.g. "Herding Group"
    akc_popularity_rank = Column(Integer, nullable=True)  # AKC 2025 popularity rank
    hip_dysplasia_pct = Column(Float, nullable=True)  # % dysplastic (OFA/BVA data)
    elbow_dysplasia_pct = Column(Float, nullable=True)  # % dysplastic elbows
    median_lifespan = Column(Float, nullable=True)  # McMillan 2024 study median (years)
    created_at = Column(DateTime, server_default=func.now())

    species = relationship("Species", back_populates="breeds")
    dogs = relationship("Dog", back_populates="breed")


class Dog(Base):
    __tablename__ = "dogs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=True)  # nullable = dog (legacy)
    breed_id = Column(Integer, ForeignKey("breeds.id"), nullable=True)
    dob = Column(Date, nullable=True)
    weight = Column(Float, nullable=True)  # kg
    sex = Column(String(10), nullable=True)  # male, female
    spayed_neutered = Column(Boolean, default=False)
    microchip_id = Column(String(50), nullable=True)
    photo_path = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    breed = relationship("Breed", back_populates="dogs")
    species = relationship("Species")
    vet_visits = relationship("VetVisit", back_populates="dog", cascade="all, delete-orphan")
    vaccinations = relationship("Vaccination", back_populates="dog", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="dog", cascade="all, delete-orphan")
    meals = relationship("Meal", back_populates="dog", cascade="all, delete-orphan")
    weight_records = relationship("WeightRecord", back_populates="dog", cascade="all, delete-orphan")
    grooming_logs = relationship("GroomingLog", back_populates="dog", cascade="all, delete-orphan")


class VetVisit(Base):
    __tablename__ = "vet_visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dog_id = Column(Integer, ForeignKey("dogs.id"), nullable=False)
    date = Column(Date, nullable=False)
    vet_name = Column(String(200), nullable=True)
    reason = Column(String(300), nullable=False)
    notes = Column(Text, nullable=True)
    cost = Column(Float, nullable=True)
    attachment_paths = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    dog = relationship("Dog", back_populates="vet_visits")


class Vaccination(Base):
    __tablename__ = "vaccinations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dog_id = Column(Integer, ForeignKey("dogs.id"), nullable=False)
    vaccine_type = Column(String(100), nullable=False)
    date_given = Column(Date, nullable=False)
    date_due = Column(Date, nullable=True)
    administered_by = Column(String(200), nullable=True)
    reminder_enabled = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    dog = relationship("Dog", back_populates="vaccinations")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dog_id = Column(Integer, ForeignKey("dogs.id"), nullable=False)
    name = Column(String(200), nullable=False)
    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    dog = relationship("Dog", back_populates="medications")


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dog_id = Column(Integer, ForeignKey("dogs.id"), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(String(50), nullable=True)  # breakfast, lunch, dinner, snack
    food_brand = Column(String(200), nullable=True)
    food_name = Column(String(200), nullable=True)
    amount = Column(String(100), nullable=True)  # e.g. "2 cups", "1 can"
    calories = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    dog = relationship("Dog", back_populates="meals")


class WeightRecord(Base):
    __tablename__ = "weight_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dog_id = Column(Integer, ForeignKey("dogs.id"), nullable=False)
    date = Column(Date, nullable=False)
    weight_kg = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    dog = relationship("Dog", back_populates="weight_records")


class GroomingLog(Base):
    __tablename__ = "grooming_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dog_id = Column(Integer, ForeignKey("dogs.id"), nullable=False)
    date = Column(Date, nullable=False)
    activity = Column(String(50), nullable=False)  # bath, nails, ears, teeth, brush, haircut
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    dog = relationship("Dog", back_populates="grooming_logs")