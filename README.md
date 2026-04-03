# TradeDesk AI — ASX Research Platform

An AI-powered trading research assistant built for the Australian Stock Exchange (ASX). TradeDesk AI combines a multi-agent LangGraph pipeline, RAG over financial documents, live market data and AI-scored sentiment into a single professional-grade research tool.

> **Run locally:** Start the server then open `http://localhost:8000/app` in your browser.
> 
> **Note:** General informational purposes only. Not personal financial advice under ASIC RG 36.

---

## What It Does

TradeDesk AI gives traders and analysts a single interface to:

- Run AI-generated research reports on any ASX stock using 4 specialist agents in parallel
- Score live news sentiment per ticker using Groq LLaMA 3.3 70B
- Ask natural language questions about company annual reports with cited answers
- Calculate risk-based position sizes using Kelly criterion and R/R ratio
- Monitor live macro data — FX, commodities, global indices and AU economic indicators

---

## Screenshots

> Screenshots can be found in `Screenshots.pdf` in the root of this repository.

---

## Panels

### 1 — Sentiment Feed

**What it does:** Fetches live news for any selected ASX tickers via Tavily and scores each article individually using Groq LLaMA 3.3 70B. Every article gets a bullish, bearish or neutral label plus a confidence score out of 100.

**How to use it:** Open the Sentiment panel, select tickers from the left sidebar (30 ASX stocks listed), click Run. Results load one ticker at a time with a 1.5 second stagger to respect Groq rate limits. Filter results by BULLISH, BEARISH or NEUTRAL using the filter buttons — each button shows a live count.

**Why it's useful:** Traders can quickly see whether news flow for a stock is bullish or bearish before entering a position, without having to read every article manually.

---

### 2 — AI Research Pipeline

**What it does:** Fires 4 LangGraph agents in parallel against any ASX ticker — a Bull Analyst, Bear Analyst, Fundamentals Analyst and Risk Assessor. Each agent independently analyses the stock using live price data (yfinance) and live news (Tavily), then a Synthesiser agent combines all 4 outputs into a final BUY / HOLD / SELL recommendation with a confidence score, sentiment label and key risk flag.

**How to use it:** Enter any ASX ticker (e.g. `CBA.AX`, `BHP.AX`) and click Run Agents. The pipeline takes approximately 30 seconds. All 4 agent outputs are shown side by side with the structured synthesis at the bottom — verdict badge, confidence bar and risk-to-watch highlight.

**Why it's useful:** Instead of one AI opinion you get 4 independent perspectives — bull case, bear case, fundamentals and risk — before a structured synthesis. This mirrors how a real investment committee works.

---

### 3 — Position Sizer

**What it does:** Calculates the optimal number of shares to buy given your account size, risk tolerance, entry price, stop loss and target. Returns risk amount, share count, position value, R/R ratio, max loss, max gain and a Kelly criterion assessment. All values update instantly as you type.

**How to use it:** Enter your account size in AUD, maximum risk per trade as a percentage, entry price, stop loss price, target price and estimated win rate. No button needed — results update live.

**Why it's useful:** Proper position sizing is the single most important factor in long-term trading survival. The Kelly criterion tells you whether your declared risk is conservative or aggressive relative to your historical win rate and R/R ratio.

---

### 4 — RAG · Document Q&A

**What it does:** Answers natural language questions about CBA's FY2025 Annual Report (229 pages) using Retrieval-Augmented Generation. The document was chunked at 150 words with 20-word overlap, embedded using `sentence-transformers/all-MiniLM-L6-v2` and stored in Qdrant Cloud. At query time, the top 6 most relevant chunks are retrieved and passed to Groq LLaMA to generate a cited answer.

**How to use it:** Type any question about the document or click a quick-question button (NIM, Risks, Dividend, CEO, CET1, Revenue). The answer appears with page citations and the number of chunks retrieved.

**Why it's useful:** Reading a 229-page annual report takes hours. RAG lets analysts instantly extract specific figures, risk disclosures, executive commentary and financial ratios with page-level citations — the same information in seconds.

---

### 5 — Macro Dashboard (conditional)

**What it does:** Displays live FX rates (AUD/USD, AUD/JPY, AUD/EUR, AUD/CNY, USD Index), commodity prices (Gold, Oil, Iron Ore, Copper, Natural Gas), global indices (ASX 200, S&P 500, Nasdaq, Dow Jones, Hang Seng, CSI 300, VIX), Australian interest rates and economic indicators, an ASX sector heatmap and a dynamic economic calendar sourced via Tavily and Groq.

**How it works:** This panel is conditionally rendered — it only appears on the home screen if yfinance successfully returns price data. Outside market hours (10:00am–4:00pm AEST Mon–Fri) it shows previous session close prices. During market hours it auto-refreshes every 60 seconds.

**Why it's useful:** Australian stocks are heavily influenced by commodity prices (iron ore, oil, gold), the AUD/USD exchange rate and China demand signals. Having all macro inputs in one view helps traders understand the broader context before running stock-level research.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (HTML/JS)                    │
│         5 panels · crimson theme · IBM Plex Mono         │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP + X-API-Key header
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                        │
│      /market  /research  /rag  /macro                    │
│   slowapi rate limiting · security headers · CORS        │
└──────┬──────────────┬────────────┬───────────────────────┘
       │              │            │
┌──────▼──────┐  ┌────▼─────┐  ┌──▼──────────────────────┐
│  LangGraph  │  │ yfinance │  │      Qdrant Cloud         │
│ Orchestrator│  │  Tavily  │  │  Vector DB · 2,266 vectors│
│             │  │  Groq    │  │  all-MiniLM-L6-v2 384-dim │
│  Bull Agent │  └──────────┘  └─────────────────────────┘
│  Bear Agent │  ← live data
│  Fund Agent │    + news
│  Risk Agent │
│      ↓      │
│  Synthesiser│
└─────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| LLM | Groq LLaMA 3.3 70B | Agent reasoning, sentiment scoring, RAG answers |
| Agents | LangGraph StateGraph | Multi-agent orchestration with parallel execution |
| Vector DB | Qdrant Cloud | Document chunk storage and similarity search |
| Embeddings | HuggingFace all-MiniLM-L6-v2 (384-dim) | Text embedding for RAG retrieval |
| Market Data | yfinance | Live ASX prices, OHLCV history, FX, commodities |
| News | Tavily | Live news search per ticker for sentiment and research |
| Backend | FastAPI | REST API, routing, input validation, rate limiting |
| Auth | X-API-Key header | API key authentication on all endpoints |
| Rate Limiting | slowapi | Per-IP rate limiting on all routes |
| Frontend | Vanilla HTML/CSS/JS | Single-page application, no framework dependency |
| Deployment | Render.com | Production hosting |

---

## RAG Ingestion Pipeline — Google Colab

The RAG panel works because CBA's FY2025 Annual Report (229 pages) was pre-processed and ingested into Qdrant Cloud using the included `colab_ingestor.ipynb` notebook. This is a one-time setup step.

### Why Colab?

Ingestion was run in Google Colab rather than locally because:
- Local machine had Anaconda environment conflicts with sentence-transformers
- Colab provides free GPU acceleration for embedding generation
- 229 pages × chunking × embedding takes ~10 minutes on Colab vs ~45 minutes locally

### How the Ingestor Works

```
1. Load PDF
   └── PyMuPDF reads the 229-page CBA Annual Report page by page

2. Chunk Text
   └── Each page split into 150-word chunks with 20-word overlap
       Overlap ensures context is not lost at chunk boundaries

3. Generate Embeddings
   └── Each chunk embedded using sentence-transformers/all-MiniLM-L6-v2
       384-dimensional dense vectors via HuggingFace Inference API

4. Store in Qdrant
   └── Each vector stored with payload:
       { text: "...", page: 42, source: "CBA_FY2025.pdf" }
       Collection: tradedesk · Total vectors: 2,266

5. Done
   └── Qdrant Cloud persists the collection permanently
       TradeDesk AI queries it at runtime via the RAG panel
```

### Running the Ingestor on a New Document

1. Open `colab_ingestor.ipynb` in Google Colab
2. Upload your PDF to the Colab session
3. Set your credentials:
```python
HF_TOKEN       = "your-huggingface-token"
QDRANT_URL     = "your-qdrant-cluster-url"
QDRANT_API_KEY = "your-qdrant-api-key"
COLLECTION     = "tradedesk"
```
4. Run all cells — completes in ~10 minutes
5. Restart TradeDesk AI — the new document is immediately queryable

**Supported document types:** Annual reports, prospectuses, ASX announcements, research reports, ASIC regulatory filings.

---

## Security

- `X-API-Key` header authentication on all API endpoints
- `slowapi` rate limiting — 5/min on research, 20/min on market data
- Regex input validation on all ticker fields (`^[A-Z0-9.\^=\-]+$`)
- HTML tag stripping on all RAG question inputs
- Security response headers — `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`
- CORS locked to `ALLOWED_ORIGINS` environment variable
- `/docs` endpoint hidden when `ENV=production`
- All secrets stored as environment variables — never in source code

---

## Running Locally

```bash
# 1. Clone
git clone https://github.com/nithish2312ds/TradeDesk-AI
cd TradeDesk-AI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in your API keys in .env

# 4. Start the server
uvicorn api.main:app --reload --port 8000

# 5. Open the app
# http://localhost:8000/app
# http://localhost:8000/docs  ← API documentation
```

---

## Environment Variables

```
GROQ_API_KEY          Groq API key — LLaMA 3.3 70B
TAVILY_API_KEY        Tavily API key — live news search
HF_TOKEN              HuggingFace token — embeddings API
QDRANT_URL            Qdrant Cloud cluster URL
QDRANT_API_KEY        Qdrant Cloud API key
TRADEDESK_API_KEY     Internal API key for request authentication
ALLOWED_ORIGINS       CORS allowed origins (use * for development)
ENV                   Set to production to hide /docs endpoint
```

---

## API Endpoints

```
GET  /market/{ticker}              Live price and fundamentals
GET  /market/{ticker}/history      OHLCV candlestick data
GET  /market/batch/watchlist       Multiple tickers in one call
GET  /market/indices/live          FX, commodities, global indices
GET  /market/rba/rate              RBA cash rate scraped from rba.gov.au
POST /research/                    Run full LangGraph multi-agent pipeline
GET  /research/sentiment/{ticker}  AI sentiment scoring with per-article breakdown
POST /rag/query                    Document Q&A with page citations
GET  /rag/status                   Qdrant connection and collection status
GET  /macro/live                   Full macro dashboard data
GET  /macro/sectors                ASX sector ETF heatmap
GET  /macro/calendar               Economic calendar via Tavily + Groq
GET  /health                       Health check
```

---

## ASIC Disclaimer

TradeDesk AI is for general informational purposes only. It does not constitute personal financial advice under ASIC Regulatory Guide 36. Always consult a licensed financial adviser before making investment decisions.

---

## Author

Built by Nithish · AI Engineer Portfolio Project · [GitHub](https://github.com/nithish2312ds)