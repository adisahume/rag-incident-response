import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

# Test OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.embeddings.create(
    input="test connection",
    model="text-embedding-3-small"
)
print("✅ OpenAI connected — embedding dimensions:", len(response.data[0].embedding))

# Test Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
print("✅ Pinecone connected — index stats:", index.describe_index_stats())