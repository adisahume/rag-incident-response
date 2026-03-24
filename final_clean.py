import json

with open("data/postmortems_structured.json", "r") as f:
    incidents = json.load(f)

print(f"Before final clean: {len(incidents)} incidents")

cleaned = []
for inc in incidents:
    # Remove non-incidents that slipped through
    skip_companies = [
        "Nat Welch's parsed postmortems",
        "Postmortem Templates",
        "Postmortems community",
        "SRE Weekly"
    ]
    if inc['company'] in skip_companies:
        print(f"  ❌ Not an incident : {inc['company']}")
        continue

    # Remove entries where GPT couldn't extract anything useful
    both_unspecified = (
        inc.get('category', '') in ['Not specified', 'Not specified.', ''] and
        inc.get('severity', '') in ['Not specified', 'Not specified.', '']
    )
    if both_unspecified:
        print(f"  ❌ No structure extracted: {inc['company']} — {inc['description'][:60]}")
        continue

    # Normalize "Not specified." → "Not specified"
    for field in ['category', 'severity', 'symptoms', 'root_cause', 'resolution', 'duration']:
        if inc.get(field, '').strip().rstrip('.') == 'Not specified':
            inc[field] = 'Not specified'

    cleaned.append(inc)

print(f"After final clean : {len(cleaned)} incidents")
print(f"Removed           : {len(incidents) - len(cleaned)} incidents")

# Show category distribution
from collections import Counter
categories = Counter(inc.get('category', 'unknown') for inc in cleaned)
severities = Counter(inc.get('severity', 'unknown') for inc in cleaned)

print(f"\n📊 Category breakdown:")
for cat, count in categories.most_common():
    bar = '█' * count
    print(f"   {cat:<20} {count:>3}  {bar}")

print(f"\n📊 Severity breakdown:")
for sev, count in severities.most_common():
    bar = '█' * count
    print(f"   {sev:<20} {count:>3}  {bar}")

with open("data/postmortems_final.json", "w") as f:
    json.dump(cleaned, f, indent=2)

print(f"\n✅ Saved to data/postmortems_final.json")
