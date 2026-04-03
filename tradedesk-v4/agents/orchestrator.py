import os
from langgraph.graph import StateGraph, START, END
from agents.state import AgentState
from tools.yfinance_tool import fetch_market_data
from tools.tavily_tool import fetch_news
from agents.bull_analyst import bull_analyst_agent
from agents.bear_analyst import bear_analyst_agent
from agents.fundamentals import fundamentals_agent
from agents.risk_assessor import risk_assessor_agent
from agents.synthesizer import synthesizer_agent


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("fetch_market_data",  fetch_market_data)
    graph.add_node("fetch_news",         fetch_news)
    graph.add_node("bull_analyst",       bull_analyst_agent)
    graph.add_node("bear_analyst",       bear_analyst_agent)
    graph.add_node("fundamentals_agent", fundamentals_agent)
    graph.add_node("risk_assessor",      risk_assessor_agent)
    graph.add_node("synthesizer",        synthesizer_agent)
    graph.add_edge(START,                "fetch_market_data")
    graph.add_edge("fetch_market_data",  "fetch_news")
    graph.add_edge("fetch_news",         "bull_analyst")
    graph.add_edge("fetch_news",         "bear_analyst")
    graph.add_edge("fetch_news",         "fundamentals_agent")
    graph.add_edge("fetch_news",         "risk_assessor")
    graph.add_edge("bull_analyst",       "synthesizer")
    graph.add_edge("bear_analyst",       "synthesizer")
    graph.add_edge("fundamentals_agent", "synthesizer")
    graph.add_edge("risk_assessor",      "synthesizer")
    graph.add_edge("synthesizer",        END)
    return graph.compile()


def run_pipeline(ticker: str) -> dict:
    print(f"\n{'='*50}\nTRADEDESK AI — Running pipeline for {ticker}\n{'='*50}")
    app = build_graph()
    initial_state: AgentState = {
        "ticker": ticker, "company_name": "", "price": 0.0,
        "change_pct": 0.0, "pe_ratio": 0.0, "dividend_yield": 0.0,
        "market_cap": "", "week_52_high": 0.0, "week_52_low": 0.0,
        "bull_thesis": None, "bear_thesis": None, "fundamentals": None,
        "risk_assessment": None, "news_headlines": None, "rag_context": None,
        "sentiment_score": None, "sentiment_label": None,
        "recommendation": None, "final_report": None, "asic_compliant": None,
    }
    final_state = app.invoke(initial_state)
    return final_state.get("final_report", {})


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    ticker = input("Enter ASX ticker (e.g. CBA.AX): ").strip().upper()
    report = run_pipeline(ticker)
    if report:
        print(f"\nFINAL: {report.get('ticker')} @ ${report.get('price')}")
        print(report.get("synthesis"))
