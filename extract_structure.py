import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_structure(incident):
    prompt = f"""
You are analyzing a software incident postmortem. Extract the following fields from the content below.
Be concise but specific. If a field is not clearly mentioned, write "Not specified".

Company: {incident['company']}
Description: {incident['description']}
Full Content: {incident.get('full_content', '')[:3000]}

Return ONLY a JSON object with exactly these fields:
{{
  "symptoms": "What engineers observed - error messages, alerts, user complaints",
  "root_cause": "The actual technical root cause of the incident",
  "resolution": "Exactly what steps were taken to fix it",
  "duration": "How long the incident lasted",
  "category": "One of: networking / database / deployment / security / hardware / configuration / dependency",
  "severity": "One of: critical / high / medium / low",
  "summary": "2-3 sentence summary combining symptoms, root cause and fix - optimized for search"
}}

Return only the JSON, no explanation, no markdown.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        text = response.choices[0].message.content.strip()
        # Clean up in case GPT adds markdown code fences
        text = text.replace("```json", "").replace("```", "").strip()
        extracted = json.loads(text)
        return extracted
    except Exception as e:
        print(f"    ⚠️  Extraction failed: {e}")
        return None

# Load enriched incidents
with open("data/postmortems_enriched.json", "r") as f:
    incidents = json.load(f)

print(f"Extracting structure from {len(incidents)} incidents using GPT...")
print(f"Estimated cost: ~${len(incidents) * 0.001:.2f}")
print(f"Estimated time: ~{len(incidents) * 3 // 60} minutes\n")

structured = []
failed = []

for i, inc in enumerate(incidents):
    print(f"[{i+1}/{len(incidents)}] {inc['company']}...", end=' ')

    extracted = extract_structure(inc)

    if extracted:
        # Merge extracted fields into incident
        inc.update(extracted)
        # Remove raw full_content to keep file size manageable
        # but keep a short version for context
        if 'full_content' in inc:
            inc['content_preview'] = inc['full_content'][:500]
            del inc['full_content']
        structured.append(inc)
        print(f"✅ {extracted.get('category', '?')} / {extracted.get('severity', '?')}")
    else:
        failed.append(inc)
        print("❌ Failed")

    # Small delay to avoid rate limiting
    time.sleep(0.5)

print(f"\n{'='*50}")
print(f"✅ Successfully structured: {len(structured)} incidents")
print(f"❌ Failed                 : {len(failed)} incidents")

# Save
with open("data/postmortems_structured.json", "w") as f:
    json.dump(structured, f, indent=2)

print(f"\n✅ Saved to data/postmortems_structured.json")

# Show 2 examples so you can verify quality
print("\n--- Sample structured incident ---")
if structured:
    sample = structured[5]
    print(f"Company   : {sample['company']}")
    print(f"Symptoms  : {sample.get('symptoms', 'N/A')}")
    print(f"Root Cause: {sample.get('root_cause', 'N/A')}")
    print(f"Resolution: {sample.get('resolution', 'N/A')}")
    print(f"Duration  : {sample.get('duration', 'N/A')}")
    print(f"Category  : {sample.get('category', 'N/A')}")
    print(f"Severity  : {sample.get('severity', 'N/A')}")
    print(f"Summary   : {sample.get('summary', 'N/A')}")