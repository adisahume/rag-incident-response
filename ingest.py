import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

def create_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def build_searchable_text(inc):
    """
    This is the most important function in the pipeline.
    We combine the most meaningful fields into one string for embedding.
    The richer this text, the better the semantic search.
    """
    parts = []

    if inc.get('symptoms') and inc['symptoms'] != 'Not specified':
        parts.append(f"Symptoms: {inc['symptoms']}")

    if inc.get('root_cause') and inc['root_cause'] != 'Not specified':
        parts.append(f"Root cause: {inc['root_cause']}")

    if inc.get('resolution') and inc['resolution'] != 'Not specified':
        parts.append(f"Resolution: {inc['resolution']}")

    if inc.get('summary'):
        parts.append(f"Summary: {inc['summary']}")

    if inc.get('description'):
        parts.append(f"Description: {inc['description']}")

    return " | ".join(parts)

# Load knowledge base
with open("data/knowledge_base.json", "r") as f:
    incidents = json.load(f)

print(f"Ingesting {len(incidents)} incidents into Pinecone...")
print(f"Estimated cost: ~$0.01\n")

success = 0
failed = 0

for i, inc in enumerate(incidents):
    try:
        # Build rich text for embedding
        searchable_text = build_searchable_text(inc)

        # Generate embedding
        embedding = create_embedding(searchable_text)

        # Build metadata — stored alongside vector, returned on retrieval
        metadata = {
            "company": inc.get("company", "Unknown"),
            "category": inc.get("category", "Not specified"),
            "severity": inc.get("severity", "Not specified"),
            "symptoms": inc.get("symptoms", "Not specified")[:500],
            "root_cause": inc.get("root_cause", "Not specified")[:500],
            "resolution": inc.get("resolution", "Not specified")[:500],
            "duration": inc.get("duration", "Not specified"),
            "summary": inc.get("summary", "")[:500],
            "description": inc.get("description", "")[:300],
            "url": inc.get("url", "")
        }

        # Upsert into Pinecone
        # ID is just the index number as a string
        index.upsert(vectors=[{
            "id": f"incident_{i}",
            "values": embedding,
            "metadata": metadata
        }])

        success += 1
        print(f"  [{i+1}/80] ✅ {inc['company']:<25} {inc.get('category','?'):<15} {inc.get('severity','?')}")

    except Exception as e:
        failed += 1
        print(f"  [{i+1}/80] ❌ {inc['company']} — Error: {e}")

    # Small delay to avoid rate limits
    time.sleep(0.3)

print(f"\n{'='*50}")
print(f"✅ Successfully ingested: {success} incidents")
print(f"❌ Failed               : {failed} incidents")

# Verify in Pinecone
stats = index.describe_index_stats()
print(f"\n📊 Pinecone index stats:")
print(f"   Total vectors: {stats['total_vector_count']}")
print(f"   Dimensions   : {stats['dimension']}")
print(f"\n✅ Knowledge base is live in Pinecone and ready for retrieval!")