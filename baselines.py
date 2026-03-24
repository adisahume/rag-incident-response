import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from rank_bm25 import BM25Okapi
import string

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── Load knowledge base for BM25 ────────────────────────────
with open("data/knowledge_base.json", "r") as f:
    knowledge_base = json.load(f)

def tokenize(text):
    """
    Convert text to lowercase tokens, remove punctuation.
    This is how BM25 works — pure keyword matching.
    """
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text.split()

# Build BM25 index from knowledge base
# Each document is the combined text of an incident
corpus_texts = []
for inc in knowledge_base:
    doc = f"{inc.get('symptoms','')} {inc.get('root_cause','')} {inc.get('resolution','')} {inc.get('description','')}"
    corpus_texts.append(doc)

tokenized_corpus = [tokenize(doc) for doc in corpus_texts]
bm25 = BM25Okapi(tokenized_corpus)

print("✅ BM25 index built from 80 knowledge base incidents")

# ── BM25 Baseline ────────────────────────────────────────────
def query_bm25(incident_description, top_k=3):
    """
    Pure keyword search — no semantic understanding.
    Returns top_k incidents by BM25 score.
    """
    tokenized_query = tokenize(incident_description)
    scores = bm25.get_scores(tokenized_query)

    # Get top_k indices sorted by score
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    matches = []
    for idx in top_indices:
        inc = knowledge_base[idx]
        matches.append({
            "score": round(float(scores[idx]), 4),
            "company": inc.get("company"),
            "category": inc.get("category"),
            "severity": inc.get("severity"),
            "symptoms": inc.get("symptoms", ""),
            "root_cause": inc.get("root_cause", ""),
            "resolution": inc.get("resolution", ""),
            "duration": inc.get("duration", ""),
            "summary": inc.get("summary", ""),
        })

    return matches

def query_bm25_with_response(incident_description, top_k=3):
    """
    BM25 retrieval + GPT synthesis.
    Same prompt as RAG but using keyword-retrieved context.
    """
    matches = query_bm25(incident_description, top_k)

    context_parts = []
    for i, match in enumerate(matches):
        part = f"""
PAST INCIDENT #{i+1} (BM25 Score: {match['score']}, Company: {match['company']})
- Symptoms   : {match['symptoms']}
- Root Cause : {match['root_cause']}
- Resolution : {match['resolution']}
- Category   : {match['category']}
"""
        context_parts.append(part)
    context = "\n".join(context_parts)

    prompt = f"""
You are an expert SRE assistant helping an on-call engineer diagnose a production incident.

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
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert SRE assistant. Be concise, specific, and actionable."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return {
        "retrieved_incidents": matches,
        "response": response.choices[0].message.content
    }

# ── No-Tool Baseline ─────────────────────────────────────────
def query_no_tool(incident_description):
    """
    Plain LLM with no retrieval at all.
    Just the incident description — no historical context.
    """
    prompt = f"""
You are an expert SRE assistant helping an on-call engineer diagnose a production incident.

CURRENT INCIDENT:
{incident_description}

You have no access to historical incident data. Based only on your general knowledge, provide:

1. LIKELY ROOT CAUSE
   What is the most probable root cause?

2. CONFIDENCE LEVEL
   High / Medium / Low — and why

3. IMMEDIATE ACTIONS (first 15 minutes)
   Numbered list of specific steps the engineer should take right now

4. MOST RELEVANT PAST INCIDENT
   Describe a well-known similar incident from your training knowledge if applicable.

5. ESCALATION NEEDED?
   Yes or No — and who should be paged if yes
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert SRE assistant. Be concise, specific, and actionable."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return {
        "retrieved_incidents": [],
        "response": response.choices[0].message.content
    }

# ── Test all 3 conditions side by side ───────────────────────
if __name__ == "__main__":
    test_query = "Our PostgreSQL database is throwing connection timeout errors. Users cannot log in. Started 10 minutes ago after a routine deployment."

    print("=" * 60)
    print("TESTING ALL 3 CONDITIONS ON SAME QUERY")
    print("=" * 60)
    print(f"Query: {test_query}\n")

    # Condition A — RAG
    from chain import query_rag
    print("\n── CONDITION A: RAG ──────────────────────────────────")
    rag_result = query_rag(test_query)
    print("Retrieved:")
    for m in rag_result['retrieved_incidents']:
        print(f"  {m['company']:<25} score: {m['score']}")
    print("\nResponse preview:")
    print(rag_result['response'][:400] + "...")

    # Condition B — BM25
    print("\n── CONDITION B: BM25 KEYWORD SEARCH ─────────────────")
    bm25_result = query_bm25_with_response(test_query)
    print("Retrieved:")
    for m in bm25_result['retrieved_incidents']:
        print(f"  {m['company']:<25} score: {m['score']}")
    print("\nResponse preview:")
    print(bm25_result['response'][:400] + "...")

    # Condition C — No Tool
    print("\n── CONDITION C: NO TOOL (plain LLM) ─────────────────")
    notool_result = query_no_tool(test_query)
    print("Retrieved: None — no retrieval used")
    print("\nResponse preview:")
    print(notool_result['response'][:400] + "...")

    print("\n✅ All 3 conditions working correctly")