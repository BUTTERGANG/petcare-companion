# Multi-Species Schema Migration (Track 2)

Design so Track 2 (cats, exotics, large animals) doesn't require a rewrite.

## Current state
Everything is dog-specific: `dogs` table, `breeds` table with dog fields, symptom list hardcoded for dogs.

## Target schema

```
Species          # dog, cat, horse, cattle, goat, bird, exotic...
├── id, name, slug, icon
└── has_breeds (bool)     # horses have breeds; rabbits less useful

Breed
├── + species_id FK       # was implicitly dog-only
└── species-specific columns stay nullable

Animal              # renamed from Dog — no column changes needed
├── species_id FK   # denormalized from breed for speed
├── breed_id FK nullable
└── name, dob, weight_kg, sex ... (all already generic)

Care tables (vet_visits, vaccinations, medications, meals,
weight_records, grooming_logs)
└── rename dog_id → animal_id. Nothing else changes.
```

## Key insight: 90% of the app is already generic

The care tables never assumed "dog" beyond the FK name. Vaccines, meals,
weights, grooming work identically for a cat or a horse. The migration is
mostly mechanical renaming + one `species_id` dimension.

## Species-specific layers (the real work)

| Layer | Dogs | Cats | Horses | Cattle |
|---|---|---|---|---|
| Vaccine schedule | Rabies, DHPP... | FVRCP, FeLV... | EWT/WN, rabies | 7-way clostridial |
| Grooming activities | bath, nails... | brush only | hoof care, deworming | — |
| Feeding math | RER×factor | RER×factor | forage-first, body condition scoring | group feeding |
| Symptom KB | 30 items | separate set | colic-focused | herd-level |
| Urgency guidance | vet/urgent/watch | same engine | "call equine vet now" thresholds | production economics |

The triage engine, reminders cron, and medical-record CRUD are shared code.
Only data differs per species.

## Migration plan (ordered)

1. **Rename `Dog`→`Animal`, add `species` table** — SQLite migration script;
   keep `/dogs/*` routes as aliases initially.
2. **Add `species_id` to Breed**, seed cats (~40 breeds reusing the AKC-style
   pipeline via TICA/CFA sources).
3. **Split symptom data into per-species JSON files** (`data/symptoms_dog.json`,
   `symptoms_cat.json`) — engine reads by species.
4. **UI: species switcher** in nav; animal cards show species icon.
5. **Large animals later**: add `herd` grouping table on Animal; feeding and
   reminders get group-level views.

## What NOT to do
- Don't build a generic "custom fields" engine — concrete columns are
  debuggable and fast.
- Don't split tables per species (`cat_visits`, `horse_visits`) — that
  multiplies every query forever.
