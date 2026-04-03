import yfinance as yf
import requests
from agents.state import AgentState

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
})

def format_market_cap(value: int) -> str:
    if value >= 1_000_000_000_000: return f"${value/1_000_000_000_000:.1f}T"
    if value >= 1_000_000_000:     return f"${value/1_000_000_000:.0f}B"
    if value >= 1_000_000:         return f"${value/1_000_000:.0f}M"
    return f"${value:,}"

def fetch_market_data(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    print(f"[yfinance] Fetching {ticker}...")
    try:
        info  = yf.Ticker(ticker, session=SESSION).info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0.0
        state["company_name"]   = info.get("longName", ticker)
        state["price"]          = round(float(price), 2)
        state["change_pct"]     = round(float(info.get("regularMarketChangePercent", 0.0) or 0.0), 2)
        state["pe_ratio"]       = round(float(info.get("trailingPE", 0.0) or 0.0), 2)
        state["dividend_yield"] = round(float(info.get("dividendYield", 0.0) or 0.0), 2)
        state["market_cap"]     = format_market_cap(info.get("marketCap", 0) or 0)
        state["week_52_high"]   = round(float(info.get("fiftyTwoWeekHigh", 0.0) or 0.0), 2)
        state["week_52_low"]    = round(float(info.get("fiftyTwoWeekLow", 0.0) or 0.0), 2)
        print(f"[yfinance] {state['company_name']} @ ${state['price']}")
    except Exception as e:
        print(f"[yfinance] Error: {e}")
        state["company_name"] = ticker
    return state
