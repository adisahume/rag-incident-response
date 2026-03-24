import json
import random

with open("data/postmortems_final.json", "r") as f:
    incidents = json.load(f)

print(f"Total incidents: {len(incidents)}")

random.seed(42)
random.shuffle(incidents)

knowledge_base = incidents[:80]
test_set = incidents[80:100]

with open("data/knowledge_base.json", "w") as f:
    json.dump(knowledge_base, f, indent=2)

with open("data/test_set.json", "w") as f:
    json.dump(test_set, f, indent=2)

print(f"✅ Knowledge base : {len(knowledge_base)} incidents → data/knowledge_base.json")
print(f"✅ Test set       : {len(test_set)} incidents → data/test_set.json")

print(f"\n--- Test set companies (verify diversity) ---")
for i, inc in enumerate(test_set):
    print(f"{i+1:2}. {inc['company']:<25} {inc.get('category','?'):<15} {inc.get('severity','?')}")