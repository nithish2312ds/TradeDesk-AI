import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from agents.state import AgentState

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"), temperature=0.2)

SYNTH_PROMPT = PromptTemplate.from_template("""
You are a senior investment analyst. Synthesise these 4 reports for {ticker} ({company_name}) at ${price}.

BULL THESIS: {bull_thesis}
BEAR THESIS: {bear_thesis}
FUNDAMENTALS: {fundamentals}
RISK ASSESSMENT: {risk_assessment}

Respond in this exact format (no markdown, no asterisks):
Overall verdict: BUY / HOLD / SELL
Confidence score: 0-100
Sentiment: BULLISH / NEUTRAL / BEARISH
Key reason: [one sentence]
Biggest risk to watch: [one sentence]

Then write 2-3 sentences of overall analysis.
This is general information only, not personal financial advice (ASIC RG36).
""")

def synthesizer_agent(state: AgentState) -> AgentState:
    print(f"[Synthesizer] Producing final report for {state['ticker']}...")
    response = llm.invoke(SYNTH_PROMPT.format(
        ticker=state["ticker"], company_name=state["company_name"],
        price=state["price"],
        bull_thesis=state.get("bull_thesis","N/A"),
        bear_thesis=state.get("bear_thesis","N/A"),
        fundamentals=state.get("fundamentals","N/A"),
        risk_assessment=state.get("risk_assessment","N/A"),
    ))
    state["final_report"] = {
        "ticker":          state["ticker"],
        "company":         state["company_name"],
        "price":           state["price"],
        "synthesis":       response.content,
        "bull_thesis":     state.get("bull_thesis"),
        "bear_thesis":     state.get("bear_thesis"),
        "fundamentals":    state.get("fundamentals"),
        "risk_assessment": state.get("risk_assessment"),
    }
    return state
