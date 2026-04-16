import os
import cohere
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def retrieve(query, top_k=3, filter_category=None):
    """
    Original retrieval without reranking.
    Used for BM25 comparison baseline.
    """
    query_embedding = get_embedding(query)

    pinecone_filter = {}
    if filter_category:
        pinecone_filter = {"category": {"$eq": filter_category}}

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter=pinecone_filter if pinecone_filter else None
    )

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

def retrieve_with_reranking(query, top_k=3):
    """
    Two-stage retrieval:
    Stage 1 — Pinecone returns top 10 candidates by vector similarity
    Stage 2 — Cohere reranks them by true semantic relevance
    Returns top_k after reranking.
    """
    # Stage 1 — get 10 candidates from Pinecone
    query_embedding = get_embedding(query)

    results = index.query(
        vector=query_embedding,
        top_k=10,
        include_metadata=True
    )

    candidates = []
    for match in results['matches']:
        candidates.append({
            "score": round(match['score'], 4),
            "company": match['metadata'].get('company'),
            "category": match['metadata'].get('category'),
            "severity": match['metadata'].get('severity'),
            "symptoms": match['metadata'].get('symptoms', ''),
            "root_cause": match['metadata'].get('root_cause', ''),
            "resolution": match['metadata'].get('resolution', ''),
            "duration": match['metadata'].get('duration', ''),
            "summary": match['metadata'].get('summary', ''),
            "url": match['metadata'].get('url', '')
        })

    if not candidates:
        return []

    # Stage 2 — Cohere reranks the 10 candidates
    # Build document strings for reranker
    docs = []
    for c in candidates:
        doc = f"""
Company: {c['company']}
Symptoms: {c['symptoms']}
Root Cause: {c['root_cause']}
Resolution: {c['resolution']}
""".strip()
        docs.append(doc)

    try:
        reranked = co.rerank(
            query=query,
            documents=docs,
            top_n=top_k,
            model="rerank-english-v3.0"
        )

        # Return reranked top_k
        reranked_matches = []
        for r in reranked.results:
            candidate = candidates[r.index]
            candidate['rerank_score'] = round(r.relevance_score, 4)
            candidate['original_rank'] = r.index + 1
            reranked_matches.append(candidate)

        return reranked_matches

    except Exception as e:
        print(f"  ⚠️  Reranking failed, falling back to vector search: {e}")
        return candidates[:top_k]


# ── Test both retrieval methods ──────────────────────────────
if __name__ == "__main__":
    test_queries = [
        "Database connection timeouts after deployment, users cannot log in",
        "DNS resolution failing, NXDOMAIN errors across all regions",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print(f"{'='*60}")

        print("\n── Without reranking (Pinecone top 3):")
        matches = retrieve(query, top_k=3)
        for i, m in enumerate(matches):
            print(f"  #{i+1} {m['company']:<25} score: {m['score']} — {m['category']}")

        print("\n── With reranking (Pinecone top 10 → Cohere top 3):")
        matches = retrieve_with_reranking(query, top_k=3)
        for i, m in enumerate(matches):
            print(f"  #{i+1} {m['company']:<25} rerank: {m['rerank_score']} (was #{m['original_rank']})")