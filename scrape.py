import requests
import json
import os
import re

# Fetch the raw markdown from danluu/post-mortems
url = "https://raw.githubusercontent.com/danluu/post-mortems/master/README.md"
response = requests.get(url)
lines = response.text.split('\n')

incidents = []
for line in lines:
    line = line.strip()
    # Format is: [Company](url). Description
    match = re.match(r'^\[(.+?)\]\((https?://[^\)]+)\)[\.:]?\s*(.*)', line)
    if match:
        company = match.group(1)
        link = match.group(2)
        description = match.group(3).strip()

        # Skip empty descriptions or section headers
        if len(description) < 10:
            continue

        incidents.append({
            "title": f"{company} incident",
            "url": link,
            "description": description,
            "company": company
        })

print(f"Found {len(incidents)} incidents")

os.makedirs("data", exist_ok=True)
with open("data/postmortems_raw.json", "w") as f:
    json.dump(incidents, f, indent=2)

print("✅ Saved to data/postmortems_raw.json")