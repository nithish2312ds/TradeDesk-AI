import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from agents.state import AgentState

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"), temperature=0.2)

FUND_PROMPT = PromptTemplate.from_template("""
You are a fundamental analyst covering ASX-listed stocks.
Analyse the financial health of {ticker} ({company_name}).

Data:
- Price: ${price}
- P/E Ratio: {pe_ratio}
- Dividend Yield: {dividend_yield}%
- 52-Week High: ${week_52_high}
- 52-Week Low: ${week_52_low}
- Market Cap: {market_cap}

Recent news:
{news_summary}

Write a fundamentals report covering:
1. Valuation assessment
2. Income/dividend quality
3. Market position
4. Overall rating: STRONG / FAIR / WEAK

Under 200 words. Use exact numbers. No markdown formatting.
""")

def fundamentals_agent(state: AgentState) -> AgentState:
    print(f"[Fundamentals] Analysing {state['ticker']}...")
    news_summary = "\n".join([f"- {h['title']}: {h['summary']}" for h in (state.get("news_headlines") or [])]) or "No recent news."
    response = llm.invoke(FUND_PROMPT.format(
        ticker=state["ticker"], company_name=state["company_name"],
        price=state["price"], pe_ratio=state["pe_ratio"],
        dividend_yield=state["dividend_yield"], week_52_high=state["week_52_high"],
        week_52_low=state["week_52_low"], market_cap=state["market_cap"],
        news_summary=news_summary
    ))
    state["fundamentals"] = response.content
    return state
