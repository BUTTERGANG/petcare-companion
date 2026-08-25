"""Feeding calculator + toxic foods data.

Vet-standard energy math:
  RER (Resting Energy Requirement) = 70 × (weight_kg ^ 0.75)
  MER (Maintenance Energy Requirement) = RER × factor
"""

# Life-stage / lifestyle factors (vet nutrition standard)
FEEDING_FACTORS = [
    {"id": "puppy_under4", "label": "Puppy (under 4 months)", "factor": 3.0},
    {"id": "puppy_over4", "label": "Puppy (4–12 months)", "factor": 2.0},
    {"id": "adult_neutered", "label": "Adult — neutered/spayed", "factor": 1.6},
    {"id": "adult_intact", "label": "Adult — intact", "factor": 1.8},
    {"id": "adult_active", "label": "Adult — very active / working", "factor": 2.0},
    {"id": "senior", "label": "Senior (7+ years)", "factor": 1.4},
    {"id": "weight_loss", "label": "Weight loss program", "factor": 1.0},
]

# Toxic / dangerous foods for dogs
TOXIC_FOODS = [
    {"food": "Chocolate", "severity": "danger", "why": "Theobromine — dogs metabolize it slowly. Dark/baking chocolate worst. Causes vomiting, seizures, heart failure.", "action": "Emergency if dark chocolate or large amount. Call vet or Pet Poison Helpline (855-764-7661)."},
    {"food": "Grapes & Raisins", "severity": "danger", "why": "Unknown toxin causes acute kidney failure. Even small amounts can be fatal. No safe dose established.", "action": "EMERGENCY — any amount warrants immediate vet contact."},
    {"food": "Xylitol (sugar-free gum, candy, peanut butter)", "severity": "danger", "why": "Causes rapid insulin release → hypoglycemia, then liver failure. Tiny amounts are deadly.", "action": "EMERGENCY — go to vet immediately, even if asymptomatic."},
    {"food": "Onions & Garlic", "severity": "danger", "why": "Damages red blood cells → anemia. Effects cumulative and delayed (3-5 days). All forms: raw, cooked, powder.", "action": "Call vet. May need bloodwork even without symptoms."},
    {"food": "Macadamia Nuts", "severity": "danger", "why": "Weakness, tremors, hyperthermia within 12 hours. Rarely fatal but distressing.", "action": "Call vet for guidance; monitor closely."},
    {"food": "Alcohol", "severity": "danger", "why": "Far more sensitive than humans — causes vomiting, CNS depression, respiratory failure.", "action": "Emergency if more than a lick."},
    {"food": "Raw Bread Dough (yeast)", "severity": "danger", "why": "Expands in stomach + produces alcohol. Causes bloat and ethanol poisoning.", "action": "Emergency — stomach may need decompression."},
    {"food": "Avocado", "severity": "caution", "why": "Persin — mild toxicity in flesh; the pit is a choking/obstruction hazard.", "action": "Keep away; call vet if pit swallowed."},
    {"food": "Cooked Bones", "severity": "caution", "why": "Splinter into sharp fragments — choking, GI perforation. Never give cooked bones of any kind.", "action": "Watch for vomiting/gagging; vet if symptoms."},
    {"food": "Corn on the Cob", "severity": "caution", "why": "The cob is indigestible — common intestinal blockage requiring surgery.", "action": "Vet if any cob chunks were swallowed."},
    {"food": "Dairy (milk, cheese in excess)", "severity": "caution", "why": "Most adult dogs are lactose intolerant → gas, diarrhea.", "action": "Small amounts usually fine; skip if sensitive."},
    {"food": "Fatty Foods / Scraps (bacon, ham, grease)", "severity": "caution", "why": "Can trigger pancreatitis — painful, sometimes fatal inflammation.", "action": "Avoid entirely; vet if vomiting + abdominal pain."},
    {"food": "Salty Snacks (chips, pretzels)", "severity": "caution", "why": "Excess salt → sodium ion poisoning in quantity: tremors, seizures.", "action": "Water access; vet if symptoms after large ingestion."},
    {"food": "Caffeine (coffee, tea, energy drinks)", "severity": "danger", "why": "Same methylxanthines as chocolate — faster absorption, no antidote.", "action": "Emergency if meaningful quantity consumed."},
    {"food": "Cherry / Peach / Plum Pits", "severity": "caution", "why": "Cyanogenic compounds in pits + obstruction risk.", "action": "Vet if pits cracked/swallowed whole."},
    {"food": "Raw Fish (salmon)", "severity": "caution", "why": "Salmon poisoning disease (parasite + bacteria) — fatal untreated.", "action": "Cook all fish; vet if lethargy/vomiting after raw fish."},
    {"food": "Salt Dough / Play-Doh (homemade)", "severity": "danger", "why": "Extremely high salt — sodium toxicosis with seizures.", "action": "Emergency — especially in small dogs."},
]


def calc_rer(weight_kg: float) -> float:
    """Resting Energy Requirement in kcal/day."""
    return 70 * (weight_kg ** 0.75)


def calc_mer(weight_kg: float, factor: float) -> float:
    """Maintenance Energy Requirement in kcal/day."""
    return calc_rer(weight_kg) * factor