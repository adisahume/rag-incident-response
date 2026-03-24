import json

with open("data/postmortems_raw.json", "r") as f:
    incidents = json.load(f)

print(f"Before cleaning: {len(incidents)} incidents")

cleaned = []
for inc in incidents:
    desc = inc['description']

    # Remove if too short
    if len(desc) < 60:
        print(f"  ❌ Too short       : {inc['company']} — {desc}")
        continue

    # Only remove if the ENTIRE purpose is a newsletter/community link
    # Be specific — not just any mention of the word
    skip_exact = [
        'usually has an **outages** section at the end',
        'with imported archive from the now-dead',
        'postmortems community'
    ]
    if any(kw in desc.lower() for kw in skip_exact):
        print(f"  ❌ Not an incident : {inc['company']} — {desc[:80]}")
        continue

    cleaned.append(inc)

print(f"\nAfter cleaning : {len(cleaned)} incidents")
print(f"Removed        : {len(incidents) - len(cleaned)} incidents")

with open("data/postmortems_clean.json", "w") as f:
    json.dump(cleaned, f, indent=2)

print("✅ Saved to data/postmortems_clean.json")