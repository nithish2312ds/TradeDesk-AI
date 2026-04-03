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
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
})

def sanitize_ticker(ticker: str) -> str:
    cleaned = ticker.strip().upper()[:20]
    if not re.match(r'^[A-Z0-9.\^=\-]+$', cleaned):
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")
    return cleaned

def format_market_cap(mc: int) -> str:
    if mc >= 1_000_000_000_000: return f"${mc/1_000_000_000_000:.1f}T"
    if mc >= 1_000_000_000:     return f"${mc/1_000_000_000:.0f}B"
    if mc >= 1_000_000:         return f"${mc/1_000_000:.0f}M"
    return f"${mc:,}"

def get_info(ticker: str) -> dict:
    return yf.Ticker(ticker, session=SESSION).info

def get_price_safe(info: dict) -> float:
    """Always returns a price — live if market open, previousClose if closed."""
    live = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
    prev = info.get("previousClose") or info.get("regularMarketPreviousClose") or 0.0
    price = float(live) if float(live) > 0 else float(prev)
    return round(price, 2)

def is_live_price(info: dict) -> bool:
    live = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
    return float(live) > 0

@router.get("/{ticker}")
@limiter.limit("60/minute")
def get_market_data(request: Request, ticker: str):
    ticker = sanitize_ticker(ticker)
    try:
        info  = get_info(ticker)
        price = get_price_safe(info)
        if not price:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")
        return {
            "ticker":         ticker,
            "company_name":   info.get("longName", ticker),
            "price":          price,
            "is_live":        is_live_price(info),
            "change_pct":     round(float(info.get("regularMarketChangePercent", 0.0) or 0.0), 2),
            "change_abs":     round(float(info.get("regularMarketChange", 0.0) or 0.0), 2),
            "pe_ratio":       round(float(info.get("trailingPE", 0.0) or 0.0), 2),
            "dividend_yield": round(float(info.get("dividendYield", 0.0) or 0.0), 2),
            "market_cap":     format_market_cap(info.get("marketCap", 0) or 0),
            "market_cap_raw": info.get("marketCap", 0) or 0,
            "week_52_high":   round(float(info.get("fiftyTwoWeekHigh", 0.0) or 0.0), 2),
            "week_52_low":    round(float(info.get("fiftyTwoWeekLow", 0.0) or 0.0), 2),
            "volume":         info.get("regularMarketVolume", 0) or 0,
            "beta":           round(float(info.get("beta", 0.0) or 0.0), 2),
            "eps":            round(float(info.get("trailingEps", 0.0) or 0.0), 2),
            "sector":         info.get("sector", ""),
            "industry":       info.get("industry", ""),
            "previous_close": round(float(info.get("previousClose", 0.0) or 0.0), 2),
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/history")
@limiter.limit("60/minute")
def get_price_history(request: Request, ticker: str, period: str = "1mo", interval: str = "1d"):
    ticker = sanitize_ticker(ticker)
    if period   not in ["1d","5d","1mo","3mo","6mo","1y","2y","5y"]:   period   = "1mo"
    if interval not in ["1m","5m","15m","30m","1h","1d","1wk","1mo"]: interval = "1d"
    try:
        hist = yf.Ticker(ticker, session=SESSION).history(period=period, interval=interval)
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No history for {ticker}")
        fmt = "%Y-%m-%d %H:%M" if interval in ["1m","5m","15m","30m","1h"] else "%Y-%m-%d"
        return {
            "ticker":   ticker,
            "period":   period,
            "interval": interval,
            "candles":  [{"date":d.strftime(fmt),"open":round(float(r.Open),2),"high":round(float(r.High),2),"low":round(float(r.Low),2),"close":round(float(r.Close),2),"volume":int(r.Volume)} for d,r in hist.iterrows()]
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/watchlist")
@limiter.limit("30/minute")
def get_watchlist(request: Request, tickers: str = "CBA.AX,BHP.AX,WBC.AX,ANZ.AX,CSL.AX,NAB.AX,FMG.AX,WDS.AX"):
    ticker_list = [sanitize_ticker(t) for t in tickers.split(",")[:20]]
    results = []
    for t in ticker_list:
        try:
            info  = get_info(t)
            price = get_price_safe(info)
            results.append({
                "ticker":         t,
                "company_name":   info.get("longName", t),
                "price":          price,
                "is_live":        is_live_price(info),
                "change_pct":     round(float(info.get("regularMarketChangePercent", 0.0) or 0.0), 2),
                "pe_ratio":       round(float(info.get("trailingPE", 0.0) or 0.0), 2),
                "dividend_yield": round(float(info.get("dividendYield", 0.0) or 0.0), 2),
                "market_cap":     format_market_cap(info.get("marketCap", 0) or 0),
                "week_52_high":   round(float(info.get("fiftyTwoWeekHigh", 0.0) or 0.0), 2),
                "week_52_low":    round(float(info.get("fiftyTwoWeekLow", 0.0) or 0.0), 2),
                "previous_close": round(float(info.get("previousClose", 0.0) or 0.0), 2),
            })
        except: pass
    return {"tickers": results, "count": len(results)}

@router.get("/indices/live")
@limiter.limit("30/minute")
def get_live_indices(request: Request):
    indices = {
        "asx200":"^AXJO","asx300":"^AXKO","audusd":"AUDUSD=X",
        "gold":"GC=F","oil":"CL=F","vix":"^VIX"
    }
    result = {}
    for name, sym in indices.items():
        try:
            info  = get_info(sym)
            price = get_price_safe(info)
            chg   = info.get("regularMarketChangePercent", 0.0) or 0.0
            result[name] = {"symbol":sym,"price":round(float(price),4),"change_pct":round(float(chg),2),"is_live":is_live_price(info)}
        except:
            result[name] = {"symbol":sym,"price":0.0,"change_pct":0.0,"is_live":False}
    return result

@router.get("/rba/rate")
@limiter.limit("10/minute")
def get_rba_rate(request: Request):
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
                            return {"rate": rate, "unit": "%", "source": "rba.gov.au"}
                    except: pass
        return {"rate": 4.10, "unit": "%", "source": "fallback"}
    except Exception as e:
        return {"rate": 4.10, "unit": "%", "source": "fallback"}
