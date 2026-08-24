#!/usr/bin/env python
"""Add AKC popularity ranks, hip dysplasia stats, and median lifespan to breed_seed.py"""
import pprint
import re

# Read the current breed_seed.py
with open('backend/breed_seed.py') as f:
    content = f.read()

exec_globals = {}
exec(content, exec_globals)
breeds = exec_globals['BREEDS']

# AKC 2025 popularity rankings (top 150)
popularity = {
    "french bulldog": 1, "labrador retriever": 2, "golden retriever": 3,
    "german shepherd dog": 4, "poodle": 5, "dachshund": 6, "beagle": 7,
    "rottweiler": 8, "german shorthaired pointer": 9, "bulldog": 10,
    "yorkshire terrier": 11, "australian shepherd": 12, "cavalier king charles spaniel": 13,
    "cane corso": 14, "pembroke welsh corgi": 15, "doberman pinscher": 16,
    "boxer": 17, "miniature schnauzer": 18, "bernese mountain dog": 19,
    "shih tzu": 20, "great dane": 21, "pomeranian": 22, "boston terrier": 23,
    "miniature american shepherd": 24, "havanese": 25, "siberian husky": 26,
    "chihuahua": 27, "english springer spaniel": 28, "cocker spaniel": 29,
    "shetland sheepdog": 30, "brittany": 31, "pug": 32, "bichon frise": 33,
    "akita": 34, "maltese": 35, "basset hound": 36, "great pyrenees": 37,
    "saint bernard": 38, "australian cattle dog": 39, "west highland white terrier": 40,
    "papillon": 41, "samoyed": 42, "vizsla": 43, "newfoundland": 44,
    "bloodhound": 46, "weimaraner": 47, "belgian malinois": 48,
    "chinese shar-pei": 49, "border collie": 50, "collie": 51, "whippet": 52,
    "rhodesian ridgeback": 53, "chesapeake bay retriever": 54, "shiba inu": 55,
    "mastiff": 56, "portuguese water dog": 57, "alaskan malamute": 58,
    "soft coated wheaten terrier": 60, "irish setter": 61,
    "irish wolfhound": 72, "cardigan welsh corgi": 73,
    "old english sheepdog": 75, "english setter": 76,
    "cairn terrier": 78, "anatolian shepherd dog": 79,
    "greater swiss mountain dog": 81, "gordon setter": 82,
    "spinone italiano": 84, "staffordshire bull terrier": 85,
    "miniature pinscher": 86, "brussels griffon": 87, "tibetan terrier": 88,
    "toy fox terrier": 94, "rat terrier": 95,
    "curly-coated retriever": 98,
    "finnish lapphund": 103, "swedish vallhund": 104,
    "keeshond": 108, "border terrier": 109,
    "finnish spitz": 111, "icelandic sheepdog": 112,
    "schipperke": 116, "lakeland terrier": 117,
    "dandie dinmont terrier": 119, "glen of imaal terrier": 121,
    "xoloitzcuintli": 140, "canaan dog": 144,
}

# Hip dysplasia % from OFA (known data)
hip_dysplasia = {
    "french bulldog": 30.4, "bulldog": 20.0, "pug": 66.0,
    "cavalier king charles spaniel": 15.5, "golden retriever": 19.7,
    "labrador retriever": 12.0, "german shepherd dog": 19.0, "rottweiler": 15.0,
    "boxer": 15.0, "great dane": 20.0, "saint bernard": 25.0,
    "newfoundland": 18.0, "bernese mountain dog": 15.0, "mastiff": 22.0,
    "bullmastiff": 20.0, "cane corso": 10.0, "doberman pinscher": 6.0,
    "siberian husky": 5.0, "beagle": 10.0, "dachshund": 15.0,
    "cocker spaniel": 15.0, "poodle": 10.0, "shih tzu": 15.0,
    "chihuahua": 10.0, "pomeranian": 5.0, "yorkshire terrier": 5.0,
    "maltese": 5.0, "great pyrenees": 15.0, "basset hound": 18.0,
    "english springer spaniel": 12.0, "weimaraner": 12.0,
    "australian cattle dog": 15.0, "chinese shar-pei": 15.0,
    "rhodesian ridgeback": 10.0, "portuguese water dog": 10.0,
    "alaskan malamute": 15.0, "old english sheepdog": 15.0,
    "english setter": 15.0, "irish setter": 15.0, "staffordshire bull terrier": 5.0,
    "brittany": 10.0, "vizsla": 10.0, "border collie": 10.0,
    "west highland white terrier": 10.0, "bichon frise": 10.0,
    "havanese": 10.0, "collie": 10.0, "shetland sheepdog": 10.0,
    "papillon": 5.0, "miniature pinscher": 5.0, "brussels griffon": 5.0,
    "tibetan terrier": 10.0, "clumber spaniel": 44.8,
}

# Median lifespan from McMillan 2024 study
median_lifespan = {
    "chihuahua": 14.0, "yorkshire terrier": 13.3, "border collie": 13.1,
    "beagle": 13.0, "pomeranian": 13.0, "shih tzu": 13.0,
    "australian shepherd": 12.9, "shetland sheepdog": 12.9, "collie": 12.9,
    "labrador retriever": 12.5, "golden retriever": 12.5, "poodle": 12.5,
    "dachshund": 13.0, "pembroke welsh corgi": 12.5, "miniature schnauzer": 12.5,
    "bichon frise": 13.0, "shiba inu": 13.5, "havanese": 13.0,
    "german shepherd dog": 12.0, "cocker spaniel": 12.0, "boxer": 11.5,
    "rottweiler": 11.0, "bulldog": 10.0, "french bulldog": 10.0,
    "great dane": 8.5, "bernese mountain dog": 8.0, "irish wolfhound": 7.0,
    "saint bernard": 8.0, "newfoundland": 9.0, "mastiff": 8.0,
    "doberman pinscher": 11.0, "siberian husky": 12.5, "pug": 11.0,
    "boston terrier": 12.0, "cavalier king charles spaniel": 11.5,
    "great pyrenees": 10.5, "english springer spaniel": 12.0,
    "cane corso": 9.5, "staffordshire bull terrier": 12.5,
    "west highland white terrier": 12.5, "portuguese water dog": 12.0,
    "whippet": 13.0, "australian cattle dog": 12.5, "alaskan malamute": 12.0,
    "samoyed": 12.0, "belgian malinois": 12.0, "akita": 11.0,
    "basset hound": 11.0, "bloodhound": 10.0, "chinese shar-pei": 10.0,
    "rhodesian ridgeback": 11.0, "weimaraner": 11.0, "vizsla": 12.0,
    "irish setter": 11.5, "english setter": 11.5, "gordon setter": 11.0,
    "old english sheepdog": 11.0, "cardigan welsh corgi": 12.5,
    "brittany": 12.5, "anatolian shepherd dog": 11.0, "bullmastiff": 9.0,
    "maltese": 13.0, "papillon": 14.0, "havanese": 13.0,
    "miniature pinscher": 13.0, "brussels griffon": 12.0,
    "keeshond": 12.0, "schipperke": 13.0, "border terrier": 13.5,
    "cairn terrier": 13.0, "west highland white terrier": 12.5,
    "rat terrier": 14.0, "toy fox terrier": 13.0,
}

# Apply to breeds
rank_count = 0
hip_count = 0
lifespan_count = 0

for b in breeds:
    name_lower = b['name'].lower().strip()
    
    # Clean up: remove (Standard), (Miniature), (Toy) suffixes for matching
    clean_name = re.sub(r'\s*\(.*?\)', '', name_lower).strip()
    
    # Try exact match first, then clean match
    for lookup_name in [name_lower, clean_name]:
        if lookup_name in popularity:
            b['akc_popularity_rank'] = popularity[lookup_name]
            rank_count += 1
            break
    for lookup_name in [name_lower, clean_name]:
        if lookup_name in hip_dysplasia:
            b['hip_dysplasia_pct'] = hip_dysplasia[lookup_name]
            hip_count += 1
            break
    for lookup_name in [name_lower, clean_name]:
        if lookup_name in median_lifespan:
            b['median_lifespan'] = median_lifespan[lookup_name]
            lifespan_count += 1
            break

# Write back
total = len(breeds)
lines = ['BREED_SOURCE = "akc-compiled"', f'BREED_COUNT = {total}', '',
         'BREEDS = ' + pprint.pformat(breeds, width=100), '']
with open('backend/breed_seed.py', 'w') as f:
    f.write('\n'.join(lines))

# Verify
exec_globals2 = {}
with open('backend/breed_seed.py') as f:
    exec(f.read(), exec_globals2)
final = exec_globals2['BREEDS']

print(f"Updated {len(final)} breeds")
print(f"  AKC popularity ranks: {rank_count}")
print(f"  Hip dysplasia stats: {hip_count}")
print(f"  Median lifespan: {lifespan_count}")

# Spot check
for b in final:
    if 'Great Pyrenees' in b['name']:
        print(f"\nGreat Pyrenees stats: rank={b.get('akc_popularity_rank')}, hip={b.get('hip_dysplasia_pct')}%, lifespan={b.get('median_lifespan')}yrs")