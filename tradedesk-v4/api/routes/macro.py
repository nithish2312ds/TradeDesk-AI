import os
import re
import yfinance as yf
import requests
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router  = APIRouter()

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

def safe_price(sym: str) -> dict:
    try:
        info  = yf.Ticker(sym, session=SESSION).info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0.0
        chg   = info.get("regularMarketChangePercent", 0.0) or 0.0
        return {"price": round(float(price), 4), "change_pct": round(float(chg), 2), "ok": True}
    except:
        return {"price": 0.0, "change_pct": 0.0, "ok": False}

@router.get("/live")
@limiter.limit("20/minute")
def get_macro(request: Request):
    # FX
    audusd = safe_price("AUDUSD=X")
    audjpy = safe_price("AUDJPY=X")
    audeur = safe_price("AUDEUR=X")
    audcny = safe_price("AUDCNY=X")

    # Commodities
    gold   = safe_price("GC=F")
    oil    = safe_price("CL=F")
    iron   = safe_price("TIO=F")
    copper = safe_price("HG=F")
    natgas = safe_price("NG=F")

    # Indices
    asx200 = safe_price("^AXJO")
    sp500  = safe_price("^GSPC")
    nasdaq = safe_price("^IXIC")
    dow    = safe_price("^DJI")
    vix    = safe_price("^VIX")

    # US 10Y
    us10y  = safe_price("^TNX")

    # RBA rate — scrape
    rba_rate = 4.10
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
                            rba_rate = rate
                            break
                    except: pass
    except: pass

    return {
        "fx": {
            "audusd": audusd,
            "audjpy": audjpy,
            "audeur": audeur,
            "audcny": audcny,
        },
        "commodities": {
            "gold":   gold,
            "oil":    oil,
            "iron":   iron,
            "copper": copper,
            "natgas": natgas,
        },
        "indices": {
            "asx200": asx200,
            "sp500":  sp500,
            "nasdaq": nasdaq,
            "dow":    dow,
            "vix":    vix,
        },
        "rates": {
            "rba":   {"price": rba_rate, "change_pct": 0.0, "ok": True},
            "us10y": us10y,
        },
        "economy": {
            "cpi":          {"value": 3.4,  "unit": "%",  "period": "Dec 2024", "label": "AU CPI"},
            "unemployment": {"value": 4.1,  "unit": "%",  "period": "Jan 2026", "label": "AU Unemployment"},
            "gdp":          {"value": 1.5,  "unit": "%",  "period": "Q3 2025",  "label": "AU GDP Growth"},
            "trade":        {"value": 5.4,  "unit": "B",  "period": "Jan 2026", "label": "Trade Balance"},
        }
    }
