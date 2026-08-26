# Reference PDF Library

Downloaded veterinary reference books backing the condition knowledge base.
Stored locally (gitignored — too large for the repo).

| Book | Pages | Covers | KB relevance |
|------|-------|--------|--------------|
| **Cat Owner's Home Veterinary Handbook** (Eldredge, fully revised) | 655 | Cats — complete owner-level reference | Cat conditions, owner_actions phrasing model |
| **Veterinary Guide for Animal Owners** (Spaulding, 2nd ed) | 473 | Cats, dogs, cattle, goats, sheep, horses | Cross-species conditions incl. our large-animal set |
| **Veterinary Technician's Daily Reference Guide: Large Animal** | 584 | Horses, cattle, sheep, goats | Large-animal clinical detail for Track 2 |
| **Standard Veterinary Treatment Guidelines for Clinics** | 541 | Multi-species treatment protocols | Treatment/therapeutics fields |
| **Rabies: Guide for Medical & Veterinary Professions** (2003) | 82 | Rabies across species | Toxicology/zoonoses entries |

## Acquisition
- pdfroom direct CDN (`f.openpdfs.org/<post_id>.pdf`) — see `~/.hermes/skills/research/pdf-hoard/SKILL.md`
- Related-book crawl from the Spaulding guide's page surfaced 5 of these 6.

## Usage plan
1. Extract text sidecars (pypdf) per book
2. Chunk by section → feed relevant chapters into KB entry drafting prompts
3. Cite as sources alongside Merck in `conditions_seed_*.py` files

## Still wanted (pdfcoffee flow currently blocked — JS-rendered download wall)
- Clinical Medicine of the Dog and Cat 3rd ed (Schaer/Gaschen)
- Veterinary Medical Guide to Dog and Cat Breeds (Bell — breed genetics!)
- BSAVA Manual of Feline Practice
- Saunders Manual of Small Animal Practice 3rd ed
