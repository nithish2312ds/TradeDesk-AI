# TradeDesk AI — ASX Research Platform v4

AI-powered trading research assistant for ASX investors.

## Stack
- LLM: Groq LLaMA 3.3 70B
- Agents: LangGraph StateGraph (parallel)
- RAG: Qdrant Cloud + HuggingFace embeddings
- Data: yfinance + Tavily
- Backend: FastAPI + slowapi
- Frontend: Vanilla HTML/CSS/JS

## Setup
pip install -r requirements.txt
cp .env.example .env
# fill in your keys
uvicorn api.main:app --reload --port 8000

## Endpoints
GET  /macro/live
GET  /market/{ticker}
GET  /market/indices/live
GET  /market/batch/watchlist
GET  /market/rba/rate
POST /research/
GET  /research/sentiment/{ticker}
POST /rag/query
GET  /rag/status
