"""Match our vocational school list against MEXT school codes.

Three matching strategies:
  a) Exact school name match
  b) Fuzzy match (normalized names)
  c) Prefecture + partial name match
"""

import csv
import json
import re
import unicodedata
import warnings
from collections import Counter, defaultdict

warnings.filterwarnings('ignore')

DATA_DIR = '/Users/shunmei/workspace/EIDP/data/mext'
SAMPLE_DIR = '/Users/shunmei/workspace/EIDP/sample'


def normalize_name(name):
    """Normalize school name for fuzzy matching."""
    if not name:
        return ''
    # NFKC normalization (full-width to half-width, etc.)
    name = unicodedata.normalize('NFKC', name)
    # Remove spaces
    name = re.sub(r'\s+', '', name)
    # Remove common suffixes/prefixes that might differ
    name = name.replace('　', '')
    return name


def extract_pref_from_code(pref_field):
    """Extract prefecture name from MEXT format like '01(北海道)'."""
    match = re.search(r'\((.+?)\)', pref_field)
    if match:
        return match.group(1)
    return pref_field


# --- Step 1: Build index from MEXT school code CSVs ---
print('=== Building MEXT school code index ===')

# Only load 専修学校 (senshu gakko) entries, type code H1
mext_schools = []
mext_by_name = defaultdict(list)
mext_by_pref_name = defaultdict(list)
mext_by_normalized = defaultdict(list)

for fname in ['school_code_east.csv', 'school_code_west.csv']:
    with open(f'{DATA_DIR}/{fname}', 'r', encoding='cp932') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 6:
                continue
            school_type = row[1]
            # H1 = 専修学校 (includes 専門学校)
            if 'H1' not in school_type:
                continue

            code = row[0]
            pref = extract_pref_from_code(row[2])
            name = row[5]
            address = row[6] if len(row) > 6 else ''
            abolished = row[9] if len(row) > 9 else ''

            entry = {
                'code': code,
                'type': school_type,
                'pref': pref,
                'name': name,
                'address': address,
                'abolished': abolished
            }
            mext_schools.append(entry)
            mext_by_name[name].append(entry)

            norm = normalize_name(name)
            mext_by_normalized[norm].append(entry)
            mext_by_pref_name[(pref, name)].append(entry)

print(f'Total 専修学校 in MEXT: {len(mext_schools)}')
active = [s for s in mext_schools if not s['abolished']]
print(f'Active (not abolished): {len(active)}')


# --- Step 2: Load our school list ---
print('\n=== Loading our school list ===')

with open(f'{DATA_DIR}/our_schools.json', 'r') as f:
    our_schools = json.load(f)

print(f'Total schools in our list: {len(our_schools)}')


# --- Step 3: Matching ---
print('\n=== Matching Results ===')

exact_matches = []
fuzzy_matches = []
pref_partial_matches = []
unmatched = []

for pref, corp, name in our_schools:
    matched = False

    # Strategy A: Exact name match
    if name in mext_by_name:
        candidates = mext_by_name[name]
        # Prefer same prefecture
        pref_matches = [c for c in candidates if c['pref'] == pref]
        if pref_matches:
            exact_matches.append((pref, corp, name, pref_matches[0]))
            matched = True
        elif candidates:
            exact_matches.append((pref, corp, name, candidates[0]))
            matched = True

    if matched:
        continue

    # Strategy B: Fuzzy match (normalized)
    norm = normalize_name(name)
    if norm in mext_by_normalized:
        candidates = mext_by_normalized[norm]
        pref_matches = [c for c in candidates if c['pref'] == pref]
        if pref_matches:
            fuzzy_matches.append((pref, corp, name, pref_matches[0]))
            matched = True
        elif candidates:
            fuzzy_matches.append((pref, corp, name, candidates[0]))
            matched = True

    if matched:
        continue

    # Strategy C: Prefecture + partial name match
    # Try to find schools in the same prefecture whose name contains ours or vice versa
    pref_schools = [s for s in mext_schools if s['pref'] == pref]
    best_match = None
    best_score = 0

    for s in pref_schools:
        s_norm = normalize_name(s['name'])
        our_norm = normalize_name(name)

        # Check if one contains the other
        if our_norm in s_norm or s_norm in our_norm:
            score = min(len(our_norm), len(s_norm)) / max(len(our_norm), len(s_norm))
            if score > best_score:
                best_score = score
                best_match = s

        # Also check common prefix length
        common = 0
        for a, b in zip(our_norm, s_norm):
            if a == b:
                common += 1
            else:
                break
        prefix_ratio = common / max(len(our_norm), 1)
        if prefix_ratio > 0.6 and prefix_ratio > best_score:
            best_score = prefix_ratio
            best_match = s

    if best_match and best_score >= 0.5:
        pref_partial_matches.append((pref, corp, name, best_match, best_score))
        matched = True

    if not matched:
        unmatched.append((pref, corp, name))


# --- Step 4: Report ---
total = len(our_schools)
print(f'\nTotal schools in our list: {total}')
print(f'\n--- Strategy A: Exact name match ---')
print(f'  Matched: {len(exact_matches)} ({len(exact_matches)/total*100:.1f}%)')

print(f'\n--- Strategy B: Fuzzy match (normalized) ---')
print(f'  Additional matched: {len(fuzzy_matches)} ({len(fuzzy_matches)/total*100:.1f}%)')

print(f'\n--- Strategy C: Pref + partial name match ---')
print(f'  Additional matched: {len(pref_partial_matches)} ({len(pref_partial_matches)/total*100:.1f}%)')

cumulative = len(exact_matches) + len(fuzzy_matches) + len(pref_partial_matches)
print(f'\n--- Cumulative ---')
print(f'  Total matched: {cumulative} ({cumulative/total*100:.1f}%)')
print(f'  Unmatched: {len(unmatched)} ({len(unmatched)/total*100:.1f}%)')

# Show some fuzzy match examples
print(f'\n--- Sample fuzzy matches ---')
for pref, corp, name, match in fuzzy_matches[:10]:
    print(f'  Our: {name}')
    print(f'  MEXT: {match["name"]} (code: {match["code"]})')
    print()

# Show some partial matches
print(f'\n--- Sample partial matches (pref + name) ---')
for item in pref_partial_matches[:10]:
    pref, corp, name, match, score = item
    print(f'  Our: [{pref}] {name}')
    print(f'  MEXT: [{match["pref"]}] {match["name"]} (code: {match["code"]}, score: {score:.2f})')
    print()

# Show some unmatched
print(f'\n--- Sample unmatched schools ---')
for pref, corp, name in unmatched[:20]:
    print(f'  [{pref}] {corp} / {name}')

# Save matching results for report
results = {
    'total': total,
    'exact_count': len(exact_matches),
    'fuzzy_count': len(fuzzy_matches),
    'partial_count': len(pref_partial_matches),
    'unmatched_count': len(unmatched),
    'exact_rate': len(exact_matches)/total*100,
    'fuzzy_rate': len(fuzzy_matches)/total*100,
    'partial_rate': len(pref_partial_matches)/total*100,
    'cumulative_rate': cumulative/total*100,
    'unmatched_rate': len(unmatched)/total*100
}

with open(f'{DATA_DIR}/matching_results.json', 'w') as f:
    json.dump(results, f, indent=2)

# Save unmatched list
with open(f'{DATA_DIR}/unmatched_schools.json', 'w') as f:
    json.dump(unmatched, f, ensure_ascii=False, indent=2)

print('\nResults saved to matching_results.json and unmatched_schools.json')
