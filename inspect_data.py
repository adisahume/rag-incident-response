import json

with open("data/postmortems_raw.json", "r") as f:
    incidents = json.load(f)

print(f"Total incidents: {len(incidents)}")
print("=" * 60)

# 1. Check for missing or empty fields
empty_desc = [i for i in incidents if not i.get('description') or len(i['description']) < 20]
empty_url = [i for i in incidents if not i.get('url')]
print(f"\n⚠️  Incidents with very short/missing description: {len(empty_desc)}")
print(f"⚠️  Incidents with missing URL: {len(empty_url)}")

# 2. Description length distribution
lengths = [len(i['description']) for i in incidents]
print(f"\n📏 Description length stats:")
print(f"   Shortest : {min(lengths)} characters")
print(f"   Longest  : {max(lengths)} characters")
print(f"   Average  : {int(sum(lengths)/len(lengths))} characters")

# 3. Company distribution
from collections import Counter
companies = Counter(i['company'] for i in incidents)
print(f"\n🏢 Top 15 companies:")
for company, count in companies.most_common(15):
    print(f"   {company:<25} {count} incidents")

# 4. Show 3 good examples
print("\n✅ 3 sample incidents:")
print("=" * 60)
for inc in incidents[5:8]:
    print(f"Company    : {inc['company']}")
    print(f"Description: {inc['description']}")
    print(f"URL        : {inc['url']}")
    print("-" * 60)

# 5. Show 3 bad/short examples
print("\n⚠️  3 shortest descriptions (potential bad data):")
print("=" * 60)
sorted_by_length = sorted(incidents, key=lambda x: len(x['description']))
for inc in sorted_by_length[:3]:
    print(f"Company    : {inc['company']}")
    print(f"Description: {inc['description']}")
    print(f"Length     : {len(inc['description'])} chars")
    print("-" * 60)