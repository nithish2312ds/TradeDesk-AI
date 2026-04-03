import os
import re
import json
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

log     = logging.getLogger("tradedesk")
limiter = Limiter(key_func=get_remote_address)
router  = APIRouter()

class ResearchRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        cleaned = v.strip().upper()
        if not re.match(r'^[A-Z0-9.\^=\-]+$', cleaned):
            raise ValueError(f"Invalid ticker: {v}")
        return cleaned

@router.post("/")
@limiter.limit("5/minute")
def run_research(request: Request, body: ResearchRequest):
    try:
        from agents.orchestrator import run_pipeline
        log.info(f"Pipeline triggered: {body.ticker}")
        report = run_pipeline(body.ticker)
        if not report:
            raise HTTPException(status_code=500, detail="Pipeline returned empty report")
        return {"status": "success", "ticker": body.ticker, "report": report}
    except HTTPException: raise
    except Exception as e:
        log.error(f"Pipeline error {body.ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/{ticker}")
@limiter.limit("15/minute")
def get_sentiment(request: Request, ticker: str):
    cleaned = ticker.strip().upper()[:10]
    if not re.match(r'^[A-Z0-9.\^=\-]+$', cleaned):
        raise HTTPException(status_code=400, detail="Invalid ticker")
    try:
        from tools.tavily_tool import fetch_news
        from agents.state import AgentState
        from langchain_groq import ChatGroq

        state: AgentState = {
            "ticker": cleaned, "company_name": cleaned,
            "price": 0.0, "change_pct": 0.0, "pe_ratio": 0.0,
            "dividend_yield": 0.0, "market_cap": "", "week_52_high": 0.0,
            "week_52_low": 0.0, "bull_thesis": None, "bear_thesis": None,
            "fundamentals": None, "risk_assessment": None, "news_headlines": None,
            "rag_context": None, "sentiment_score": None, "sentiment_label": None,
            "recommendation": None, "final_report": None, "asic_compliant": None,
        }
        state    = fetch_news(state)
        headlines = state.get("news_headlines") or []
        if not headlines:
            return {"ticker": cleaned, "score": 50, "label": "NEUTRAL", "reason": "No news found", "articles": [], "count": 0}

        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"), temperature=0.1)

        articles = []
        for h in headlines[:5]:
            try:
                resp = llm.invoke(f"""Score this news for {cleaned}.
Return ONLY valid JSON: score (0-100), label (BULLISH/NEUTRAL/BEARISH), summary (one sentence).
No markdown. Raw JSON only.
Headline: {h['title']}
Content: {h['summary'][:200]}""")
                raw  = resp.content.strip().replace("```json","").replace("```","").strip()
                data = json.loads(raw)
                articles.append({"title": h["title"], "source": h.get("source",""), "url": h.get("url",""), "score": int(data.get("score",50)), "label": data.get("label","NEUTRAL"), "summary": data.get("summary","")})
            except:
                articles.append({"title": h["title"], "source": h.get("source",""), "url": h.get("url",""), "score": 50, "label": "NEUTRAL", "summary": h.get("summary","")[:150]})

        overall = round(sum(a["score"] for a in articles) / len(articles))
        label   = "BULLISH" if overall>=60 else "BEARISH" if overall<=40 else "NEUTRAL"

        try:
            news_text   = "\n".join([f"- {a['title']}" for a in articles])
            reason_resp = llm.invoke(f"One sentence summary of market sentiment for {cleaned} based on:\n{news_text}\nOne sentence only:")
            reason      = reason_resp.content.strip()
        except:
            reason = f"{len(articles)} news sources analysed."

        return {"ticker": cleaned, "score": overall, "label": label, "reason": reason, "articles": articles, "count": len(articles)}

    except HTTPException: raise
    except Exception as e:
        log.error(f"Sentiment error {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
