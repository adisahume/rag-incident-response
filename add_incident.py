import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

def add_incident(company, description, url="", 
                 symptoms="", root_cause="", 
                 resolution="", category="", severity=""):
    """
    Add a single new incident to the live Pinecone knowledge base.
    Can be called manually or from an automated pipeline.
    """

    # Step 1 — If full details not provided, use GPT to extract them
    if not symptoms or not root_cause:
        print(f"  Extracting structure with GPT...")
        prompt = f"""
Extract incident details from this description.
Company: {company}
Description: {description}

Return ONLY JSON:
{{
  "symptoms": "what engineers observed",
  "root_cause": "technical root cause",
  "resolution": "how it was fixed",
  "category": "networking/database/deployment/security/hardware/configuration",
  "severity": "critical/high/medium/low",
  "summary": "2-3 sentence summary"
}}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        text = response.choices[0].message.content.strip()
        text = text.replace("```json","").replace("```","").strip()
        extracted = json.loads(text)
        symptoms   = extracted.get("symptoms", "")
        root_cause = extracted.get("root_cause", "")
        resolution = extracted.get("resolution", "")
        category   = extracted.get("category", "")
        severity   = extracted.get("severity", "")
        summary    = extracted.get("summary", "")
    else:
        summary = f"{company}: {description[:200]}"

    # Step 2 — Build searchable text
    searchable_text = f"""
Symptoms: {symptoms} |
Root cause: {root_cause} |
Resolution: {resolution} |
Summary: {summary} |
Description: {description}
"""

    # Step 3 — Generate embedding
    print(f"  Generating embedding...")
    response = client.embeddings.create(
        input=searchable_text,
        model="text-embedding-3-small"
    )
    embedding = response.data[0].embedding

    # Step 4 — Get current vector count to generate unique ID
    stats = index.describe_index_stats()
    current_count = stats['total_vector_count']
    new_id = f"incident_{current_count + 1}"

    # Step 5 — Upsert into Pinecone
    print(f"  Upserting to Pinecone as {new_id}...")
    index.upsert(vectors=[{
        "id": new_id,
        "values": embedding,
        "metadata": {
            "company": company,
            "category": category,
            "severity": severity,
            "symptoms": symptoms[:500],
            "root_cause": root_cause[:500],
            "resolution": resolution[:500],
            "summary": summary[:500],
            "description": description[:300],
            "url": url,
            "ingested_at": time.strftime("%Y-%m-%d")
        }
    }])

    # Step 6 — Save to local JSON log so you have a record
    log_entry = {
        "id": new_id,
        "company": company,
        "description": description,
        "symptoms": symptoms,
        "root_cause": root_cause,
        "resolution": resolution,
        "category": category,
        "severity": severity,
        "url": url,
        "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Append to running log
    log_path = "data/dynamic_incidents.json"
    try:
        with open(log_path, "r") as f:
            log = json.load(f)
    except FileNotFoundError:
        log = []

    log.append(log_entry)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    print(f"  ✅ Added {new_id} — {company} ({category} / {severity})")
    print(f"  📊 Knowledge base now has {current_count + 1} incidents")
    return new_id


# ── Test it with a real recent incident ─────────────────────
if __name__ == "__main__":
    print("Adding a new incident to the live knowledge base...\n")

    add_incident(
        company="Cloudflare",
        description="""On November 18, 2025, a change in permissions in a 
        database in Cloudflare's bot-detection systems caused a file to be 
        output that exceeded the limits of the software that runs that system. 
        That file was propagated throughout Cloudflare's network, causing a 
        systemwide outage affecting CDN, Workers, and Zero Trust products.""",
        url="https://blog.cloudflare.com/18-november-2025-outage/",
        category="configuration",
        severity="critical"
    )