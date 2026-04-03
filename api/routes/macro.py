import os
import json
import time
import logging
import yfinance as yf
import requests
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

log     = logging.getLogger("tradedesk")
limiter = Limiter(key_func=get_remote_address)
router  = APIRouter()

# ── Cache ──────────────────────────────────────────────────────────
_cache = {}
CACHE_TTL = 300

def cache_get(key):
    if key in _cache:
        val, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
    return None

def cache_set(key, val):
    _cache[key] = (val, time.time())

# ── Use yf.download() — less blocked than .info ────────────────────
def safe_ticker(sym: str) -> dict:
    try:
        df = yf.download(sym, period="2d", interval="1d", progress=False, auto_adjust=True)
        if df.empty:
            return {"price": 0.0, "change_pct": 0.0, "is_live": False, "ok": False}
        closes = df["Close"].squeeze()
        if len(closes) >= 2:
            prev  = float(closes.iloc[-2])
            last  = float(closes.iloc[-1])
            chg   = ((last - prev) / prev) * 100 if prev else 0.0
        else:
            last  = float(closes.iloc[-1])
            chg   = 0.0
        return {"price": round(last, 4), "change_pct": round(chg, 2), "is_live": True, "ok": True}
    except Exception as e:
        log.warning(f"safe_ticker {sym}: {e}")
        return {"price": 0.0, "change_pct": 0.0, "is_live": False, "ok": False}

# ── MAIN MACRO ─────────────────────────────────────────────────────
@router.get("/live")
@limiter.limit("20/minute")
def get_macro(request: Request):
    cached = cache_get("macro_live")
    if cached:
        return cached

    fx = {
        "audusd": safe_ticker("AUDUSD=X"),
        "audjpy": safe_ticker("AUDJPY=X"),
        "audeur": safe_ticker("AUDEUR=X"),
        "audcny": safe_ticker("AUDCNY=X"),
        "dxy":    safe_ticker("DX-Y.NYB"),
    }
    commodities = {
        "gold":   safe_ticker("GC=F"),
        "oil":    safe_ticker("CL=F"),
        "iron":   safe_ticker("TIO=F"),
        "copper": safe_ticker("HG=F"),
        "natgas": safe_ticker("NG=F"),
    }
    indices = {
        "asx200": safe_ticker("^AXJO"),
        "sp500":  safe_ticker("^GSPC"),
        "nasdaq": safe_ticker("^IXIC"),
        "dow":    safe_ticker("^DJI"),
        "vix":    safe_ticker("^VIX"),
        "hsi":    safe_ticker("^HSI"),
        "csi300": safe_ticker("000300.SS"),
    }
    rates = {
        "rba":   {"price": _scrape_rba_rate(), "change_pct": 0.0, "is_live": True, "ok": True},
        "us10y": safe_ticker("^TNX"),
        "au10y": safe_ticker("^AGBD"),
    }
    economy = _fetch_au_economy()

    result = {
        "fx": fx, "commodities": commodities,
        "indices": indices, "rates": rates,
        "economy": economy, "fetched_at": time.time(),
    }
    cache_set("macro_live", result)
    return result

# ── SECTORS ────────────────────────────────────────────────────────
SECTOR_ETFS = {
    "Financials":    "XFJ.AX",
    "Materials":     "XMJ.AX",
    "Healthcare":    "XHJ.AX",
    "Energy":        "XEJ.AX",
    "Industrials":   "XIJ.AX",
    "Consumer Disc": "XDJ.AX",
    "Real Estate":   "XPJ.AX",
    "Utilities":     "XUJ.AX",
    "Consumer Stap": "XSJ.AX",
    "Info Tech":     "XTJ.AX",
}

@router.get("/sectors")
@limiter.limit("10/minute")
def get_sectors(request: Request):
    cached = cache_get("sectors")
    if cached:
        return cached
    results = []
    for name, sym in SECTOR_ETFS.items():
        d = safe_ticker(sym)
        results.append({
            "name":       name,
            "symbol":     sym,
            "change_pct": d["change_pct"],
            "is_live":    d["is_live"],
            "ok":         d["ok"],
        })
    results.sort(key=lambda x: x["change_pct"], reverse=True)
    out = {"sectors": results, "fetched_at": time.time()}
    cache_set("sectors", out)
    return out

# ── CALENDAR ───────────────────────────────────────────────────────
@router.get("/calendar")
@limiter.limit("5/minute")
def get_calendar(request: Request):
    cached = cache_get("calendar")
    if cached:
        return cached
    events = _fetch_economic_calendar()
    out = {"events": events, "fetched_at": time.time()}
    cache_set("calendar", out)
    return out

def _fetch_economic_calendar() -> list:
    try:
        from tavily import TavilyClient
        from langchain_groq import ChatGroq
        client  = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        results = client.search(
            query="Australia economic calendar RBA meeting CPI GDP employment release dates 2026",
            max_results=5, search_depth="basic"
        )
        content = "\n\n".join([r.get("content","")[:400] for r in results.get("results",[])])
        if not content.strip():
            return _rba_fallback_events()
        llm  = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"), temperature=0.0)
        resp = llm.invoke(f"""Extract Australian economic calendar events from the text below.
Return ONLY a JSON array with keys: date (YYYY-MM-DD), event (string), importance (HIGH/MEDIUM/LOW).
Include only future events or events within the last 7 days. Max 10 events.
No markdown, no backticks, raw JSON array only.
Text: {content}
JSON array:""")
        raw    = resp.content.strip().replace("```json","").replace("```","").strip()
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed[:10]
    except Exception as e:
        log.warning(f"Calendar fetch error: {e}")
    return _rba_fallback_events()

def _rba_fallback_events() -> list:
    events = []
    try:
        from bs4 import BeautifulSoup
        r    = requests.get("https://www.rba.gov.au/monetary-policy/int-rate-decisions/", timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr")[:12]:
            cells = row.find_all("td")
            if len(cells) >= 1:
                date_text = cells[0].get_text(strip=True)
                if "2026" in date_text or "2025" in date_text:
                    events.append({"date": date_text, "event": "RBA Interest Rate Decision", "importance": "HIGH"})
    except Exception as e:
        log.warning(f"RBA scrape error: {e}")
    return events[:8]

def _scrape_rba_rate() -> float:
    try:
        from bs4 import BeautifulSoup
        r    = requests.get("https://www.rba.gov.au/statistics/cash-rate/", timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    try:
                        rate = float(cells[-1].text.strip().replace("%",""))
                        if 0.1 < rate < 6.0:
                            return rate
                    except: pass
    except: pass
    return 4.10

def _fetch_au_economy() -> dict:
    try:
        from tavily import TavilyClient
        from langchain_groq import ChatGroq
        client  = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        results = client.search(query="Australia CPI inflation unemployment rate GDP growth latest 2026", max_results=3, search_depth="basic")
        content = "\n\n".join([r.get("content","")[:300] for r in results.get("results",[])])
        llm     = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"), temperature=0.0)
        resp    = llm.invoke(f"""Extract the latest Australian economic indicators from the text.
Return ONLY a JSON object with keys: cpi (number), unemployment (number), gdp (number), trade_balance (number).
No units in the value. No markdown. Raw JSON only.
Text: {content}
JSON:""")
        raw    = resp.content.strip().replace("```json","").replace("```","").strip()
        parsed = json.loads(raw)
        return {
            "cpi":           {"value": parsed.get("cpi", 0),           "label": "AU CPI"},
            "unemployment":  {"value": parsed.get("unemployment", 0),  "label": "Unemployment"},
            "gdp":           {"value": parsed.get("gdp", 0),           "label": "GDP Growth"},
            "trade_balance": {"value": parsed.get("trade_balance", 0), "label": "Trade Balance"},
        }
    except Exception as e:
        log.warning(f"Economy fetch error: {e}")
        return {
            "cpi":           {"value": 0, "label": "AU CPI"},
            "unemployment":  {"value": 0, "label": "Unemployment"},
            "gdp":           {"value": 0, "label": "GDP Growth"},
            "trade_balance": {"value": 0, "label": "Trade Balance"},
        }