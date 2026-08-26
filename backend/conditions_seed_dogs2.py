"""Veterinary condition knowledge base — dog seed data (batch 2).

Structured entries designed for both owner guidance and professional lookup.
Each entry: species-linked, urgency-tiered, with symptoms/causes/diagnosis/
treatment/prevention/owner-actions/emergency-flags.
"""


def _c(species, name, slug, category, urgency, summary, symptoms, causes,
       diagnosis, treatment, prevention, breeds, actions, emergency, sources):
    return {
        "species": species, "name": name, "slug": slug, "category": category,
        "urgency": urgency, "summary": summary, "symptoms": symptoms,
        "causes": causes, "diagnosis": diagnosis, "treatment": treatment,
        "prevention": prevention, "breed_predispositions": breeds,
        "owner_actions": actions, "when_emergency": emergency, "sources": sources,
    }


CONDITIONS = [
    _c("dog", "Addison's Disease (Hypoadrenocorticism)", "addisons-disease", "endocrine", "chronic",
       "The adrenal glands stop producing cortisol and aldosterone, so the body cannot respond to stress or regulate sodium and potassium. Signs wax and wane for months, then a crisis can strike suddenly and be fatal within hours.",
       ["Lethargy that comes and goes", "Recurrent vomiting/diarrhea", "Poor appetite with weight loss", "Increased thirst and urination", "Shaking/trembling", "Weakness or collapse during stressful events"],
       ["Immune-mediated destruction of the adrenal cortex (most common)", "Sudden withdrawal of long-term steroid medication", "Pituitary disease (rare)", "Medications like trilostane used for Cushing's"],
       "Basal cortisol screen followed by ACTH stimulation test (definitive). Bloodwork classically shows high potassium with low sodium; a sodium:potassium ratio under 27 is strongly suggestive.",
       "Lifelong mineralocorticoid replacement (fludrocortisone or desoxycorticosterone pivalate injections every 3-4 weeks) plus prednisone. Doses are increased during illness, travel, or surgery.",
       "No true prevention since most cases are autoimmune. Inform all caretakers of the diagnosis so steroid coverage is given before stressful events; never abruptly stop steroid therapy.",
       ["Standard Poodle", "Bearded Collie", "Portuguese Water Dog", "Nova Scotia Duck Tolling Retriever", "Great Dane", "Rottweiler", "West Highland White Terrier"],
      "Keep a written crisis plan and injectable/extra medication on hand. Double doses of steroids are typically needed for vet visits, boarding, or travel — confirm with your vet.",
      "Collapse, inability to stand, severe vomiting, or weak 'waxy' gums in a diagnosed or suspected dog = emergency NOW. An Addisonian crisis is fatal without IV fluids and steroids within hours.",
      ["Merck Veterinary Manual — Hypoadrenocorticism in Dogs"]),

    _c("dog", "Cataracts", "cataracts", "ophthalmic", "monitor",
       "The lens of the eye becomes cloudy and opaque, blocking light and gradually causing vision loss. Cataracts range from tiny incidental spots to complete blindness, and some progress painfully via lens-induced uveitis or glaucoma.",
       ["Gray/blue-white cloudiness inside the pupil", "Bumping into furniture or walls", "Reluctance to use stairs or jump", "Clumsiness in dim light", "Redness or squinting (if inflamed)", "Apprehension in new environments"],
       ["Inherited/genetic predisposition (most common cause in purebreds)", "Diabetes mellitus (cataracts develop rapidly, often within weeks)", "Age-related hardening of the lens", "Eye trauma", "Toxins, radiation, or intraocular inflammation"],
       "Veterinary ophthalmic exam with slit-lamp biomicroscopy distinguishes cataracts from harmless nuclear sclerosis. Blood glucose testing to rule out diabetes; ultrasound and electroretinography before surgery to check retinal health.",
       "Surgical removal of the lens by phacoemulsification, usually with an artificial lens implant, is the only cure and restores vision in ~90% of suitable patients. Anti-inflammatory drops control lens-induced inflammation; untreated diabetic dogs often need surgery sooner.",
       "Choose breeding stock screened through OFA/ACVO eye exams (annual certification). Keep diabetic dogs tightly regulated and have their eyes checked at least twice yearly. Promptly treat any eye inflammation.",
       ["Miniature Schnauzer", "Golden Retriever", "Labrador Retriever", "Cocker Spaniel", "Poodle (all varieties)", "Boston Terrier", "Australian Shepherd", "Siberian Husky"],
      "Photograph the eyes monthly to track cloudiness. Keep furniture layout consistent and use scent cues while vision declines. Any redness, squinting, or sudden worsening warrants a same-week ophthalmology visit.",
      "A painful red eye, bulging eye surface, or sudden total blindness = same-day emergency. Lens-induced glaucoma destroys sight quickly even in already-cloudy eyes.",
      ["Merck Veterinary Manual — Disorders of the Lens", "ACVO eye examination registry"]),

    _c("dog", "Degenerative Myelopathy", "degenerative-myelopathy", "neurologic", "chronic",
       "A progressive disease of the spinal cord in which the insulating sheath around nerves degenerates, slowly paralyzing the hindquarters over 6 months to 2 years. It causes no pain but is relentlessly disabling and ultimately fatal.",
       ["Wobbling/scuffing hind gait", "Dragging rear toenails (audible scraping on pavement)", "Difficulty rising from lying down", "Knuckling over on hind paws", "Crossing of hind legs when walking", "Progression to hind-limb paralysis, then loss of bladder/bowel control"],
       ["SOD1 gene mutation (autosomal recessive with incomplete penetrance)", "Age-related oxidative damage to spinal cord tissue"],
       "Diagnosis is largely by ruling out other causes: MRI to exclude disc disease and tumors, plus DNA testing for SOD1 status. Definitive confirmation only on post-mortem examination.",
       "No curative treatment exists. Intensive physical rehabilitation (underwater treadmill, balance exercises), mobility carts once hind legs weaken, paw booties, and bladder management late in disease. Some evidence suggests moderate lifelong exercise slows progression.",
       "Test breeding animals for the SOD1 mutation and avoid pairing two carriers. Keep adult dogs lean and fit — good muscle condition delays disability onset in genetically at-risk dogs.",
       ["German Shepherd Dog", "Boxer", "Pembroke Welsh Corgi", "Rhodesian Ridgeback", "Chesapeake Bay Retriever", "Cardigan Welsh Corgi"],
      "Start physical therapy as soon as gait changes appear — early rehab preserves function longest. Trim rear nails weekly and protect knuckling paws. Plan ahead for cart fitting and home modifications (rugs on slippery floors).",
      "Sudden rather than gradual paralysis, back pain, or crying out = NOT typical DM — seek same-day care, as it suggests IVDD or another treatable problem instead.",
      ["Merck Veterinary Manual — Degenerative Myelopathy", "OFAs SOD1 test documentation"]),

    _c("dog", "Demodectic Mange (Demodicosis)", "demodectic-mange", "parasitic", "chronic",
       "Overgrowth of Demodex mites, which live harmlessly in the hair follicles of most healthy dogs. When a young or immunocompromised dog's immune system fails to keep them in check, mites multiply and cause patchy hair loss and skin infection.",
       ["Patchy hair loss (often around eyes, muzzle, forelegs)", "Red, scaly, or greasy skin", "Pimples/pustules and crusts", "Secondary deep pyoderma with draining tracts", "Itching (usually mild unless secondary infection)"],
       ["Immature immune system in puppies under 18 months", "Inherited immune defect predisposing generalized disease", "Immunosuppressive drugs (chemotherapy, steroids)", "Underlying illness such as cancer, hypothyroidism, or Cushing's"],
       "Deep skin scraping or hair pluck examined under the microscope reveals large numbers of cigar-shaped mites at all life stages. Adult-onset cases warrant bloodwork and imaging to hunt for an underlying immunosuppressive disease.",
       "Many localized cases resolve without treatment; isoxazoline class oral parasiticides (fluralaner, afoxolaner, sarolaner) have revolutionized therapy and clear most dogs in 4-8 weeks. Treat secondary bacterial infections with appropriate antibiotics and medicated baths.",
       "No vaccine exists. Do not breed dogs that had generalized demodicosis as the tendency is inherited. Keep puppies well-nourished and dewormed so their developing immune systems are not stressed.",
       ["American Pit Bull Terrier", "Staffordshire Terrier", "Shar-Pei", "Bulldog", "Boston Terrier", "Great Dane", "West Highland White Terrier"],
      "Isolate affected bedding and wash it hot. Do not use over-the-counter dips without veterinary guidance. Photograph lesions weekly to track whether patches are spreading beyond the original site.",
      "Fever, lethargy, rapidly spreading painful skin, or draining wounds = same-day vet. Deep secondary infections can become systemic and require aggressive care.",
      ["Merck Veterinary Manual — Mange in Dogs", "AAVP parasitology guidelines"]),

    _c("dog", "Canine Gastric Ulcers", "gastric-ulcers-dog", "gastrointestinal", "urgent",
       "Open sores develop in the stomach lining when its protective mucus barrier is breached by acid, causing pain, bleeding, and sometimes perforation. Often silent until vomiting blood or black tarry stool appears.",
       ["Vomiting (sometimes with blood or 'coffee grounds' material)", "Black tarry stool (digested blood)", "Poor appetite", "Weight loss", "Abdominal discomfort after meals", "Pale gums/anemia in chronic cases"],
       ["Long-term NSAID use (the leading cause)", "Corticosteroid therapy, especially combined with NSAIDs", "Mast cell tumors releasing histamine", "Severe stress/illness (spinal disease, sepsis)", "Liver or kidney failure", "Helicobacter infection"],
       "Gastroscopy is definitive and allows biopsy of ulcers and suspicious tissue. Bloodwork checks anemia and organ function; fecal occult blood supports ongoing bleeding.",
       "Stop the offending drug immediately. Proton pump inhibitors (omeprazole) plus sucralfate for 4-8 weeks; treat underlying mast cell tumor or systemic disease. Surgery for perforation or uncontrolled hemorrhage.",
       "Never give human NSAIDs (ibuprofen, naproxen) to dogs — many formulations are toxic at small doses. Use vet-prescribed NSAIDs only at labeled doses with food, avoid combining them with steroids, and discuss stomach protection for long-term users.",
       ["Greyhound (NSAID sensitivity)", "Sled dogs and working dogs on long-term anti-inflammatory regimens", "Dogs with mast cell tumors"],
      "If your dog takes daily NSAIDs, learn the early warning signs and schedule periodic bloodwork. Give medications with food. Report any dark stool or reduced appetite within days rather than waiting it out.",
      "Vomiting fresh blood, large amounts of coffee-ground vomit, black tarry stool, weakness, or collapse = emergency NOW — significant GI bleeding can be fatal without transfusion.",
      ["Merck Veterinary Manual — Gastric Ulcers in Small Animals"]),

    _c("dog", "Glaucoma (Canine)", "glaucoma-dog", "ophthalmic", "urgent",
       "Pressure inside the eye builds up because fluid cannot drain properly, damaging the retina and optic nerve. It is one of the most painful eye conditions in dogs and can cause permanent blindness within 24-72 hours untreated.",
       ["Red, bloodshot eye", "Cloudy/bluish cornea", "Enlarged or bulging eyeball", "Squinting and light sensitivity", "Excessive tearing", "Vision loss/bumping into things", "Behavioral withdrawal from pain"],
       ["Inherited abnormal drainage angle (goniodysgenesis) — primary glaucoma", "Secondary causes: lens luxation, uveitis, cataracts, tumors, trauma"],
       "Tonometry measures intraocular pressure (normal ~15-25 mmHg; glaucoma often >40). Gonioscopy of the drainage angle distinguishes primary from secondary disease; ultrasound evaluates lens position and masses behind the cornea.",
       "Emergency pressure reduction with topical (latanoprost, timolol) and IV (mannitol) medications, followed by lifelong drops 2-3 times daily. For blind, end-stage eyes: enucleation or intrascleral prosthesis gives lasting comfort. Treat any underlying cause in secondary glaucoma.",
       "Have predisposed breeds screened with gonioscopy before 5 years old so prophylactic drops can begin. Any red or cloudy eye in an at-risk breed should get a tonometry check the same day — never wait.",
       ["Basset Hound", "American Cocker Spaniel", "Shiba Inu", "Chow Chow", "Siberian Husky", "Boston Terrier", "Wire Fox Terrier", "Great Dane"],
      "Learn what your dog's normal eyes look like and check daily if predisposed. Never delay evaluation of a red eye — owners frequently mistake glaucoma for simple conjunctivitis. Administer prescribed drops exactly on schedule once diagnosed.",
      "A suddenly red, cloudy, painful, or enlarged eye = same-day EMERGENCY. Vision lost to pressure damage does not return; every hour counts.",
      ["Merck Veterinary Manual — Glaucoma in Dogs", "ACVO glaucoma consensus statement"]),
]

