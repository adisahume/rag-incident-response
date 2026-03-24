import json
import requests
from bs4 import BeautifulSoup
import time

def fetch_full_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove noise
        for tag in soup(['nav', 'header', 'footer', 'script', 
                        'style', 'aside', 'menu']):
            tag.decompose()
        
        # Get clean text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Return first 4000 chars — enough for GPT to extract structure
        return text[:4000] if len(text) > 4000 else text
        
    except Exception as e:
        return None

# Load clean incidents
with open("data/postmortems_clean.json", "r") as f:
    incidents = json.load(f)

print(f"Fetching full content for {len(incidents)} incidents...")
print("This will take 5-10 minutes. Don't close the terminal.\n")

enriched = []
failed = []

for i, inc in enumerate(incidents):
    print(f"[{i+1}/{len(incidents)}] Fetching {inc['company']}...", end=' ')
    
    content = fetch_full_content(inc['url'])
    
    if content and len(content) > 200:
        inc['full_content'] = content
        enriched.append(inc)
        print(f"✅ {len(content)} chars")
    else:
        failed.append(inc)
        print(f"❌ Failed")
    
    # Be polite to servers
    time.sleep(1.5)

print(f"\n{'='*50}")
print(f"✅ Successfully fetched: {len(enriched)} incidents")
print(f"❌ Failed/dead links  : {len(failed)} incidents")

# Save both
with open("data/postmortems_enriched.json", "w") as f:
    json.dump(enriched, f, indent=2)

with open("data/postmortems_failed.json", "w") as f:
    json.dump(failed, f, indent=2)

print(f"\n✅ Saved enriched data to data/postmortems_enriched.json")