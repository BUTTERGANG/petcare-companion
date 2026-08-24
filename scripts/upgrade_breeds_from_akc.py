#!/usr/bin/env python
"""Upgrade breed_seed.py with authoritative AKC data from the open akcdata.csv + breed_traits.csv datasets."""
import csv
import pprint
import re
import sys

sys.path.insert(0, '.')
from backend.breed_seed import BREEDS

# ---------- Load AKC datasets ----------
with open('/tmp/akcdata.csv') as f:
    reader = csv.DictReader(f)
    akc_rows = list(reader)

with open('/tmp/breed_traits.csv') as f:
    reader = csv.DictReader(f)
    trait_rows = list(reader)
    trait_by_breed = {}
    for r in trait_rows:
        breed = r['Breed'].replace('\u00a0', ' ').strip().lower()
        trait_by_breed[breed] = r

# ---------- Normalization helpers ----------
def norm_name(s):
    s = s.lower().strip()
    # Poodle (Standard) -> poodle standard
    s = re.sub(r'\((\w+)\)$', r' \1', s)
    s = s.replace('-', ' ')
    return s

# Build akc lookup: normalized name -> row
akc_by_name = {}
for r in akc_rows:
    name = r[''].strip()
    akc_by_name[norm_name(name)] = r
    akc_by_name[norm_name(name).rstrip('s')] = r

def find_akc(our_name):
    n = norm_name(our_name)
    if n in akc_by_name:
        return akc_by_name[n]
    if n.rstrip('s') in akc_by_name:
        return akc_by_name[n.rstrip('s')]
    # try partial
    for k, v in akc_by_name.items():
        if k in n or n in k:
            return v
    return None

def find_traits(our_name):
    n = norm_name(our_name)
    if n in trait_by_breed:
        return trait_by_breed[n]
    if n.rstrip('s') in trait_by_breed:
        return trait_by_breed[n.rstrip('s')]
    for k, v in trait_by_breed.items():
        if k in n or n in k:
            return v
    return None

# ---------- Map AKC data into our breed schema ----------
size_cat_map = {
    'toy': 'toy', 'small': 'small', 'medium': 'medium',
    'large': 'large', 'giant': 'giant',
}

updated = 0
traits_merged = 0
for b in BREEDS:
    akc = find_akc(b['name'])
    if not akc:
        continue
    updated += 1

    # Height/weight/lifespan -> keep as-is if we have them, else use AKC
    try:
        min_w = float(akc['min_weight']); max_w = float(akc['max_weight'])
        if not b.get('weight_range_min'):
            b['weight_range_min'] = round(min_w, 1)
        if not b.get('weight_range_max'):
            b['weight_range_max'] = round(max_w, 1)
    except (ValueError, TypeError):
        pass

    try:
        min_l = akc['min_expectancy']; max_l = akc['max_expectancy']
        if min_l and max_l:
            b['lifespan_years'] = f"{int(float(min_l))}-{int(float(max_l))}"
    except (ValueError, TypeError):
        pass

    # Group -> append to care_notes or origin if we don't have origin
    grp = akc.get('group', '')
    if grp and not b.get('origin'):
        b['origin'] = grp

    # Temperament keywords from AKC
    akc_temp = akc.get('temperament', '')
    if akc_temp and not b.get('temperament'):
        b['temperament'] = akc_temp

    # Grooming / shedding / energy / trainability from AKC categories
    if not b.get('grooming_freq'):
        b['grooming_freq'] = akc.get('grooming_frequency_category', None) or None
    if not b.get('shedding_level'):
        sc = akc.get('shedding_category', '').lower()
        if 'hypoallergenic' in sc or 'infrequent' in sc or 'non' in sc:
            b['shedding_level'] = 'low'
        elif 'seasonal' in sc or 'occasional' in sc:
            b['shedding_level'] = 'moderate'
        elif 'frequent' in sc or 'lots' in sc or 'regular' in sc:
            b['shedding_level'] = 'high'
    if not b.get('energy_level'):
        ec = akc.get('energy_level_category', '').lower()
        if 'regular' in ec:
            b['energy_level'] = 'moderate'
        elif 'energetic' in ec or 'vigorous' in ec or 'very' in ec:
            b['energy_level'] = 'high'
        else:
            b['energy_level'] = 'moderate'
    if not b.get('trainability'):
        tc = akc.get('trainability_category', '').lower()
        if 'eager' in tc or 'easy' in tc or 'agreeable' in tc:
            b['trainability'] = 'easy'
        elif 'stubborn' in tc or 'challenging' in tc:
            b['trainability'] = 'challenging'
        else:
            b['trainability'] = 'moderate'

    # Description -> care_notes if we don't have any
    if not b.get('care_notes') and akc.get('description'):
        b['care_notes'] = akc['description'][:600]

    # AKC group
    if grp:
        b['akc_group'] = grp

    # Traits 1-5 from breed_traits
    tr = find_traits(b['name'])
    if tr:
        traits_merged += 1
        # Add AKC 1-5 trait scores as structured data
        b['akc_traits'] = {
            'affectionate_with_family': tr.get('Affectionate With Family'),
            'good_with_young_children': tr.get('Good With Young Children'),
            'good_with_other_dogs': tr.get('Good With Other Dogs'),
            'shedding_level': tr.get('Shedding Level'),
            'coat_grooming_frequency': tr.get('Coat Grooming Frequency'),
            'drooling_level': tr.get('Drooling Level'),
            'coat_type': tr.get('Coat Type'),
            'coat_length': tr.get('Coat Length'),
            'openness_to_strangers': tr.get('Openness To Strangers'),
            'playfulness_level': tr.get('Playfulness Level'),
            'watchdog_protective': tr.get('Watchdog/Protective Nature'),
            'adaptability_level': tr.get('Adaptability Level'),
            'trainability_level': tr.get('Trainability Level'),
            'energy_level': tr.get('Energy Level'),
            'barking_level': tr.get('Barking Level'),
            'mental_stimulation_needs': tr.get('Mental Stimulation Needs'),
        }
        # Map key traits into our schema if we don't have them
        if not b.get('good_with_kids') and tr.get('Good With Young Children'):
            v = tr.get('Good With Young Children')
            b['good_with_kids'] = {'1': 'Poor', '2': 'Fair', '3': 'Good', '4': 'Very good', '5': 'Excellent'}.get(v, v)
        if not b.get('good_with_dogs') and tr.get('Good With Other Dogs'):
            v = tr.get('Good With Other Dogs')
            b['good_with_dogs'] = {'1': 'Poor', '2': 'Fair', '3': 'Good', '4': 'Very good', '5': 'Excellent'}.get(v, v)

# ---------- Write upgraded seed ----------
total = len(BREEDS)
lines = ['BREED_SOURCE = "akc-compiled"', f'BREED_COUNT = {total}', '',
         'BREEDS = ' + pprint.pformat(BREEDS, width=100), '']
with open('backend/breed_seed.py', 'w') as f:
    f.write('\n'.join(lines))

# Verify
exec_globals = {}
with open('backend/breed_seed.py') as f:
    exec(f.read(), exec_globals)
final = exec_globals['BREEDS']
print(f"Written {len(final)} breeds, count={exec_globals['BREED_COUNT']}")
print(f"Updated from AKC: {updated}")
print(f"With AKC 1-5 traits: {traits_merged}")
with_traits = sum(1 for b in final if 'akc_traits' in b)
print(f"Total breeds with akc_traits: {with_traits}")

# Spot check Great Pyrenees
for b in final:
    if 'Pyrenees' in b['name'] and 'Great' in b['name']:
        print("\n--- Great Pyrenees (upgraded) ---")
        for k, v in b.items():
            if k != 'akc_traits':
                print(f"  {k}: {v}")
        print(f"  akc_traits: {b['akc_traits']}")
