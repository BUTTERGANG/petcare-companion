# PetCare Companion 🐾

A pet care companion web app — medical records, breed reference, nutrition tracking, and symptom checker for your dogs.

## Quick Start

```bash
cd ~/code/petcare-companion
python3 -m venv venv
source venv/bin/activate
pip install -e .
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

## Features

- **Dashboard** — dog cards, upcoming vaccine reminders, active medications, recent vet visits
- **Medical Records** — vet visits, vaccinations (with due-date reminders), medications (active/archive toggle)
- **Nutrition Tracking** — log meals (brand, food, amount, calories) and weight history
- **Symptom Checker** — 30 common symptoms with 3 urgency levels (emergency / urgent / monitor) + care advice
- **Breed Reference** — 123 breeds with AKC trait scorecards, popularity rankings, hip dysplasia prevalence, and median lifespan data

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI (Python 3.11+) |
| Database | SQLite (SQLAlchemy async) |
| Frontend | Tailwind CSS + Jinja2 templates |
| Storage | Local file uploads |

## Project Structure

```
backend/
├── main.py          # 31 routes
├── models.py        # 6 data models
├── schemas.py       # Pydantic validation
├── database.py      # SQLAlchemy engine
└── breed_seed.py    # 123 AKC-verified breeds
templates/           # 18 Jinja2 templates
scripts/             # Data upgrade utilities
```

## Data Sources

Breed data sourced from:
- **AKC** (American Kennel Club) — breed traits, group, popularity ranks
- **OFA** (Orthopedic Foundation for Animals) — hip dysplasia prevalence
- **McMillan et al. 2024** — peer-reviewed median lifespan data