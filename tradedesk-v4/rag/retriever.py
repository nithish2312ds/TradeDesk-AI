import os
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from qdrant_client import QdrantClient
from langchain_groq import ChatGroq

embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
)

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"), temperature=0.1)

def query_documents(question: str, collection_name: str = "tradedesk") -> dict:
    print(f"[Retriever] Query: {question}")
    client  = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    q_vec   = embeddings.embed_query(question)
    results = client.query_points(collection_name=collection_name, query=q_vec, limit=4).points
    if not results:
        return {"answer": "No relevant information found in documents.", "sources": [], "question": question}
    context = "\n\n".join([f"[Page {r.payload['page']}]\n{r.payload['text']}" for r in results])
    prompt  = f"""You are a financial analyst assistant.
Answer using ONLY the document context below.
If not found, say "Not found in documents."
Always cite the page number.

Context:
{context}

Question: {question}
Answer:"""
    response = llm.invoke(prompt)
    sources  = [{"page": r.payload.get("page","?"), "score": round(r.score,3), "snippet": r.payload.get("text","")[:150]} for r in results]
    return {"answer": response.content, "sources": sources, "question": question}
