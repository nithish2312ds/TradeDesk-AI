import os
import re
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

log     = logging.getLogger("tradedesk")
limiter = Limiter(key_func=get_remote_address)
router  = APIRouter()

class QueryRequest(BaseModel):
    question:   str = Field(..., min_length=3, max_length=500)
    collection: str = Field(default="tradedesk", max_length=50)

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v):
        cleaned = re.sub(r'<[^>]+>', '', v).strip()
        if len(cleaned) < 3:
            raise ValueError("Question too short")
        return cleaned

    @field_validator("collection")
    @classmethod
    def sanitize_collection(cls, v):
        if not re.match(r'^[a-z0-9_\-]+$', v):
            raise ValueError("Invalid collection name")
        return v

@router.post("/query")
@limiter.limit("20/minute")
def query_rag(request: Request, body: QueryRequest):
    try:
        from rag.retriever import query_documents
        log.info(f"RAG query: {body.question[:60]}")
        result = query_documents(question=body.question, collection_name=body.collection)
        return {"status": "success", "question": result["question"], "answer": result["answer"], "sources": result["sources"], "chunks": len(result.get("sources",[]))}
    except HTTPException: raise
    except Exception as e:
        log.error(f"RAG error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
@limiter.limit("10/minute")
def rag_status(request: Request):
    try:
        from qdrant_client import QdrantClient
        client      = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
        collections = [c.name for c in client.get_collections().collections]
        counts      = {col: client.count(collection_name=col).count for col in collections}
        return {"status": "connected", "collections": collections, "counts": counts, "total": sum(counts.values())}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
