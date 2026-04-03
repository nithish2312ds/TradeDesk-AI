import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from agents.state import AgentState

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"), temperature=0.2)

RISK_PROMPT = PromptTemplate.from_template("""
You are a risk analyst covering ASX-listed stocks.
Assess investment risk for {ticker} ({company_name}).

Data:
- Price: ${price}
- P/E Ratio: {pe_ratio}
- Dividend Yield: {dividend_yield}%
- 52-Week High: ${week_52_high}
- 52-Week Low: ${week_52_low}
- Market Cap: {market_cap}

Recent news:
{news_summary}

Write a risk assessment covering:
1. Market risk
2. Sector risk
3. Regulatory risk (APRA, ASIC, RBA)
4. Recommended max position size
5. Overall risk rating: LOW / MEDIUM / HIGH

This is general information only, not personal financial advice (ASIC RG36).
Under 200 words. No markdown formatting.
""")

def risk_assessor_agent(state: AgentState) -> AgentState:
    print(f"[Risk Assessor] Assessing {state['ticker']}...")
    news_summary = "\n".join([f"- {h['title']}: {h['summary']}" for h in (state.get("news_headlines") or [])]) or "No recent news."
    response = llm.invoke(RISK_PROMPT.format(
        ticker=state["ticker"], company_name=state["company_name"],
        price=state["price"], pe_ratio=state["pe_ratio"],
        dividend_yield=state["dividend_yield"], week_52_high=state["week_52_high"],
        week_52_low=state["week_52_low"], market_cap=state["market_cap"],
        news_summary=news_summary
    ))
    state["risk_assessment"] = response.content
    return state
