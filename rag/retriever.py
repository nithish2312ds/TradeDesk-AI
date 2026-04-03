import os
import requests
from qdrant_client import QdrantClient
from langchain_groq import ChatGroq

HF_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"

def get_embedding(text: str) -> list:
    headers  = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}
    response = requests.post(
        HF_API_URL,
        headers=headers,
        json={"inputs": [text]}
    )
    if response.status_code != 200:
        raise Exception(f"HuggingFace API error {response.status_code}: {response.text}")
    result = response.json()
    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
        return result[0]
    return result

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1
)

def query_documents(question: str, collection_name: str = "tradedesk") -> dict:
    print(f"[Retriever] Searching: {question}")
    try:
        client   = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        q_vector = get_embedding(question)
        print(f"[Retriever] Embedding dim: {len(q_vector)}")

        try:
            results = client.query_points(
                collection_name=collection_name,
                query=q_vector,
                limit=6
            ).points
        except AttributeError:
            results = client.search(
                collection_name=collection_name,
                query_vector=q_vector,
                limit=6
            )

        if not results:
            return {"answer": "No relevant information found in the indexed documents.", "sources": [], "question": question}

        context = "\n\n".join([
            f"[Page {r.payload.get('page','?')}]\n{r.payload.get('text','')}"
            for r in results
        ])

        prompt = f"""You are a financial analyst assistant analysing the CBA FY2025 Annual Report.

Use the document context below to answer the question as helpfully as possible.
- If the exact answer is in the context, state it clearly and cite the page number.
- If only partial information is available, share what you found and note it may be incomplete.
- If the context contains no relevant information at all, say so briefly.
- Do not make up information. Base your answer only on the context provided.

Context:
{context}

Question: {question}

Answer:"""

        response = llm.invoke(prompt)
        sources  = [
            {"page": r.payload.get("page","?"), "score": round(r.score,3), "snippet": r.payload.get("text","")[:150]}
            for r in results
        ]
        print(f"[Retriever] Done — {len(results)} chunks retrieved.")
        return {"answer": response.content, "sources": sources, "question": question}

    except Exception as e:
        print(f"[Retriever] Error: {e}")
        raise