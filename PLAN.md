# PetCare Companion — Development Plan

## Current State

**Status:** MVP complete + Phase 2 shipped. All 31 routes verified returning 200. Server live on `http://localhost:8000`.

Built as a FastAPI PWA (server-rendered Jinja2 + Tailwind) that serves two jobs:
1. **Medical care companion** — per-dog medical records (vet visits, vaccinations, medications, nutrition, weight)
2. **Breed reference library** — 123 dog breeds sourced from AKC data

**Test health:** No formal test suite yet. All 31 routes verified manually via curl (every endpoint returns 200). Real data flow verified: create dog → log meal/weight → records appear on nutrition dashboard.

**Note:** The project is **not yet a git repo** locally, despite being built for eventual Replit hosting.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI (Python 3.11+) |
| Database | SQLite via SQLAlchemy (async, aiosqlite) |
| Validation | Pydantic v2 |
| Frontend | Tailwind CSS (CDN) + Jinja2 server-rendered templates |
| Auth | None yet (single-user local app) |
| Image storage | Local `uploads/` dir |
| Hosting | Local uvicorn; Replit targeted next |

---

## Data Models (6 tables)

| Table | Purpose |
|-------|---------|
| **Breed** | 123 breeds w/ AKC traits, group, popularity rank, hip dysplasia %, median lifespan |
| **Dog** | Profiles (name, breed FK, DOB, weight, sex, microchip, photo, notes) |
| **VetVisit** | date, vet, reason, notes, cost |
| **Vaccination** | type, given/due dates, reminder toggle |
| **Medication** | name, dosage, frequency, active toggle |
| **Meal** | nutrition logs (meal type, brand, food, amount, calories) |
| **WeightRecord** | weight tracking over time |

---

## API Implementation

**31 routes** across 6 feature areas:

| Area | Routes |
|------|--------|
| Dashboard | `GET /` |
| Dogs | add, detail, edit, delete |
| Vet visits | list, add, delete |
| Vaccinations | list, add, delete |
| Medications | list, add, toggle active, delete |
| Nutrition | dashboard, add meal, delete meal, add weight, delete weight |
| Symptom checker | list (30 symptoms), detail |
| Breeds | list (search + size filter), detail |

**Response style:** HTML pages (server-rendered). No JSON API yet.

---

## Security Posture

- **No auth yet** — single local user. Must add auth before Replit/online hosting.
- No CSRF protection (none needed for local single-user, but required once online).
- Uploads stored locally with no file-type validation.
- Symptom checker displays clear "not veterinary advice" disclaimer.

---

## MVP / Roadmap

### ✅ Done
- [x] Dog profiles (CRUD)
- [x] Medical records: vet visits, vaccinations, medications
- [x] 123-breeds reference database (AKC-sourced)
- [x] Dashboard with upcoming vaccine reminders + active meds
- [x] AKC trait scorecard (1–5 visuals) + breed stats (popularity, hip dysplasia %, median lifespan)
- [x] Nutrition tracking (meals + weight)
- [x] Symptom checker (30 symptoms, 3 urgency levels)

### 🔜 Short-term (next 2 weeks)
- [ ] Init git repo + commit, push to GitHub
- [ ] Prept for Replit: `replit.toml`, ensure SQLite works on Replit
- [ ] Auth (simple login) — required before online hosting
- [ ] Vaccine due-date cron reminders (models exist, not wired)

### 🗓️ Medium-term (next 2 months)
- [ ] Backfill breed data gaps (34 breeds without AKC trait scorecard)
- [ ] OFA elbow dysplasia + more health statistics
- [ ] Weight-trend chart (visualize weight over time)
- [ ] Attachment uploads for vet visits (receipts)

### 🌌 Long-term
- [ ] Cross-device sync (Neon/Postgres migration)
- [ ] Mobile-friendly PWA install
- [ ] Multi-user support

---

## For Replit

Deployment target. Prep needed:
- Create git repo, push to GitHub first
- Add `replit.toml` with uvicorn run command
- SQLite file path must be writable on Replit
- Add auth before making public