from typing import TypedDict, Optional, Annotated

def keep_last(a, b):
    if b is None:
        return a
    return b

class AgentState(TypedDict):
    ticker:           Annotated[str,            keep_last]
    company_name:     Annotated[str,            keep_last]
    price:            Annotated[float,          keep_last]
    change_pct:       Annotated[float,          keep_last]
    pe_ratio:         Annotated[float,          keep_last]
    dividend_yield:   Annotated[float,          keep_last]
    market_cap:       Annotated[str,            keep_last]
    week_52_high:     Annotated[float,          keep_last]
    week_52_low:      Annotated[float,          keep_last]
    news_headlines:   Annotated[Optional[list], keep_last]
    bull_thesis:      Annotated[Optional[str],  keep_last]
    bear_thesis:      Annotated[Optional[str],  keep_last]
    fundamentals:     Annotated[Optional[str],  keep_last]
    risk_assessment:  Annotated[Optional[str],  keep_last]
    rag_context:      Annotated[Optional[str],  keep_last]
    sentiment_score:  Annotated[Optional[int],  keep_last]
    sentiment_label:  Annotated[Optional[str],  keep_last]
    recommendation:   Annotated[Optional[str],  keep_last]
    final_report:     Annotated[Optional[dict], keep_last]
    asic_compliant:   Annotated[Optional[bool], keep_last]
