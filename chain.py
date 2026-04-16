import os
from dotenv import load_dotenv
from openai import OpenAI
from retriever import retrieve

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_context(matches):
    """
    Formats retrieved incidents into a clean context block for GPT.
    """
    context_parts = []
    for i, match in enumerate(matches):
        part = f"""
PAST INCIDENT #{i+1} (Similarity: {match['score']}, Company: {match['company']})
- Symptoms    : {match['symptoms']}
- Root Cause  : {match['root_cause']}
- Resolution  : {match['resolution']}
- Duration    : {match['duration']}
- Category    : {match['category']}
- Severity    : {match['severity']}
"""
        context_parts.append(part)
    return "\n".join(context_parts)

def query_rag(incident_description, top_k=3):
    """
    Full RAG pipeline:
    1. Retrieve similar past incidents
    2. Build context from retrieved incidents
    3. Send to GPT for structured response
    """
    # Step 1 — Retrieve
    matches = retrieve_with_reranking(incident_description, top_k=top_k)

    # Step 2 — Build context
    context = build_context(matches)

    # Step 3 — Synthesize with GPT
    prompt = f"""
You are an expert SRE (Site Reliability Engineer) assistant helping an on-call engineer 
diagnose and resolve a production incident.

CURRENT INCIDENT:
{incident_description}

SIMILAR PAST INCIDENTS FROM KNOWLEDGE BASE:
{context}

Based on the similar past incidents above, provide a structured response:

1. LIKELY ROOT CAUSE
   What is the most probable root cause based on patterns from past incidents?

2. CONFIDENCE LEVEL
   High / Medium / Low — and why

3. IMMEDIATE ACTIONS (first 15 minutes)
   Numbered list of specific steps the engineer should take right now

4. MOST RELEVANT PAST INCIDENT
   Which past incident is most similar and what exactly fixed it?

5. ESCALATION NEEDED?
   Yes or No — and who should be paged if yes

Be specific and actionable. An engineer is reading this under pressure.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert SRE assistant. Be concise, specific, and actionable. Engineers are reading this during a live incident."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    answer = response.choices[0].message.content

    return {
        "incident": incident_description,
        "retrieved_incidents": matches,
        "response": answer
    }

# ── Test the full pipeline ───────────────────────────────────
if __name__ == "__main__":
    test_query = "Our PostgreSQL database is throwing connection timeout errors. Users cannot log in. Started 10 minutes ago after a routine deployment."

    print("🔍 Running full RAG pipeline...")
    print(f"Query: {test_query}\n")
    print("=" * 60)

    result = query_rag(test_query)

    print("\n📚 RETRIEVED PAST INCIDENTS:")
    for i, match in enumerate(result['retrieved_incidents']):
        print(f"  #{i+1} {match['company']} (score: {match['score']}) — {match['category']}")

    print("\n🤖 RAG RESPONSE:")
    print("=" * 60)
    print(result['response'])