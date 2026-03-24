import os
import json
import time
import requests
import hashlib
from add_incident import add_incident

def get_url_hash(url):
    """Create a unique fingerprint for each URL"""
    return hashlib.md5(url.encode()).hexdigest()

def load_seen_urls():
    """Load URLs we've already ingested"""
    try:
        with open("data/seen_urls.json", "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_seen_urls(seen):
    with open("data/seen_urls.json", "w") as f:
        json.dump(list(seen), f)

def check_for_new_incidents():
    """
    Fetches the danluu postmortems repo and ingests
    any incidents not yet in our knowledge base.
    """
    print(f"[{time.strftime('%H:%M:%S')}] Checking for new incidents...")

    seen_urls = load_seen_urls()

    # Fetch latest from GitHub
    url = "https://raw.githubusercontent.com/danluu/post-mortems/master/README.md"
    response = requests.get(url)
    lines = response.text.split('\n')

    import re
    new_count = 0

    for line in lines:
        line = line.strip()
        match = re.match(r'^\[(.+?)\]\((https?://[^\)]+)\)[\.:]?\s*(.*)', line)
        if not match:
            continue

        company = match.group(1)
        inc_url = match.group(2)
        description = match.group(3).strip()

        # Skip if too short or already seen
        if len(description) < 60:
            continue
        if inc_url in seen_urls:
            continue
        # Skip if too short or already seen
        if len(description) < 60:
            continue
        if inc_url in seen_urls:
            continue

        # Skip known junk entries
        skip_companies = [
            "Nat Welch's parsed postmortems",
            "Postmortem Templates",
            "Postmortems community",
            "SRE Weekly"
        ]
        if company in skip_companies:
            continue

        # New incident found — add it
        print(f"\n  🆕 New incident found: {company}")
        try:
            add_incident(
                company=company,
                description=description,
                url=inc_url
            )
            seen_urls.add(inc_url)
            save_seen_urls(seen_urls)
            new_count += 1
            time.sleep(2)  # be polite to APIs
        except Exception as e:
            print(f"  ❌ Failed to add: {e}")

    if new_count == 0:
        print(f"  No new incidents found")
    else:
        print(f"\n✅ Added {new_count} new incidents to knowledge base")

    return new_count


if __name__ == "__main__":
    # Initialize seen_urls from your existing knowledge base
    # so we don't re-ingest what's already there
    try:
        with open("data/knowledge_base.json", "r") as f:
            kb = json.load(f)
        seen = set(inc.get('url','') for inc in kb if inc.get('url'))

        with open("data/test_set.json", "r") as f:
            ts = json.load(f)
        seen.update(inc.get('url','') for inc in ts if inc.get('url'))

        with open("data/seen_urls.json", "w") as f:
            json.dump(list(seen), f)
        print(f"✅ Initialized with {len(seen)} already-seen URLs")
    except:
        pass

    # Run once immediately
    check_for_new_incidents()

    # Then run every 24 hours
    print(f"\n⏰ Monitoring for new incidents every 24 hours...")
    print(f"   Press Ctrl+C to stop\n")

    while True:
        time.sleep(86400)  # 24 hours
        check_for_new_incidents()