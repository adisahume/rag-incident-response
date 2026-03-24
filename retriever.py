import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def retrieve(query, top_k=3, filter_category=None):
    """
    Takes an incident description and returns top_k most similar
    historical incidents from Pinecone.
    
    filter_category: optionally filter by category e.g. "networking"
    """
    # Convert query to embedding
    query_embedding = get_embedding(query)

    # Build filter if category specified
    pinecone_filter = {}
    if filter_category:
        pinecone_filter = {"category": {"$eq": filter_category}}

    # Search Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter=pinecone_filter if pinecone_filter else None
    )

    # Format results cleanly
    matches = []
    for match in results['matches']:
        matches.append({
            "score": round(match['score'], 4),
            "company": match['metadata'].get('company'),
            "category": match['metadata'].get('category'),
            "severity": match['metadata'].get('severity'),
            "symptoms": match['metadata'].get('symptoms'),
            "root_cause": match['metadata'].get('root_cause'),
            "resolution": match['metadata'].get('resolution'),
            "duration": match['metadata'].get('duration'),
            "summary": match['metadata'].get('summary'),
            "url": match['metadata'].get('url')
        })

    return matches

# ── Test it with 3 real queries ──────────────────────────────
if __name__ == "__main__":

    test_queries = [
        "Our database is down, queries are timing out and users can't log in",
        "DNS resolution is failing, users getting NXDOMAIN errors",
        "Deployment went wrong, new version is throwing 500 errors in production"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print(f"{'='*60}")

        matches = retrieve(query, top_k=3)

        for i, match in enumerate(matches):
            print(f"\n  Result #{i+1} — Similarity: {match['score']}")
            print(f"  Company   : {match['company']}")
            print(f"  Category  : {match['category']}")
            print(f"  Symptoms  : {match['symptoms'][:100]}...")
            print(f"  Root Cause: {match['root_cause'][:100]}...")
            print(f"  Resolution: {match['resolution'][:100]}...")