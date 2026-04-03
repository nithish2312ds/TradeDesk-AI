import os
from tavily import TavilyClient
from agents.state import AgentState

def fetch_news(state: AgentState) -> AgentState:
    ticker  = state["ticker"]
    company = state.get("company_name", ticker)
    print(f"[Tavily] Searching news for {company}...")
    try:
        client  = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        results = client.search(
            query=f"{company} {ticker} ASX stock news 2026",
            max_results=5,
            search_depth="basic"
        )
        state["news_headlines"] = [
            {"title": r.get("title",""), "summary": r.get("content","")[:300], "url": r.get("url",""), "source": r.get("source","")}
            for r in results.get("results", [])
        ]
        print(f"[Tavily] Found {len(state['news_headlines'])} articles")
    except Exception as e:
        print(f"[Tavily] Error: {e}")
        state["news_headlines"] = []
    return state
