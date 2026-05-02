import json
import os
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from .llm import get_llm
from .prompts import (
    DISCOVERY_PROMPT_TEMPLATE,
    SYNTHESIZER_PROMPT_TEMPLATE,
    load_skill,
)
from .state import AnalyzerState
from .sub_agents import (
    _flatten_content,
    fundamental_node,
    onchain_node,
    sentiment_node,
    technical_node,
    tokenomics_node,
)
from .tools import get_search_tool

REPORTS_DIR = Path(os.environ.get("ANALYZER_REPORTS_DIR", "reports"))


def _strip_code_fence(text: str) -> str:
    """Remove a wrapping ```...``` fence if present."""
    text = text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
    return text


def discovery_node(state: AnalyzerState) -> dict:
    agent = create_react_agent(
        get_llm("discovery"),
        tools=[get_search_tool()],
        prompt=DISCOVERY_PROMPT_TEMPLATE.format(user_input=state["symbol"]),
    )
    result = agent.invoke(
        {"messages": [HumanMessage(content=f"Resolve and profile: {state['symbol']}")]}
    )
    raw = _flatten_content(result["messages"][-1].content)
    try:
        profile = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError:
        profile = {
            "ticker": state["symbol"].upper(),
            "name": state["symbol"],
            "category": "Other",
            "_discovery_error": "Failed to parse JSON; minimal profile used.",
            "_raw": raw[:500],
        }
    return {"token_profile": profile}


def synthesizer_node(state: AnalyzerState) -> dict:
    llm = get_llm("synthesis")
    orchestrator_skill = load_skill("crypto-analyze/SKILL.md")
    prompt = SYNTHESIZER_PROMPT_TEMPLATE.format(
        orchestrator_skill=orchestrator_skill,
        token_profile_json=json.dumps(state["token_profile"], indent=2),
        onchain=state.get("onchain_report", "_(missing)_"),
        tokenomics=state.get("tokenomics_report", "_(missing)_"),
        sentiment=state.get("sentiment_report", "_(missing)_"),
        technical=state.get("technical_report", "_(missing)_"),
        fundamental=state.get("fundamental_report", "_(missing)_"),
    )
    result = llm.invoke(
        [
            SystemMessage(content="You are the Crypto Analysis Synthesizer."),
            HumanMessage(content=prompt),
        ]
    )
    final = _flatten_content(result.content)

    ticker = state["token_profile"].get("ticker", state["symbol"]).upper()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"CRYPTO-ANALYSIS-{ticker}.md"
    out_path.write_text(final)
    return {"final_report": final, "output_path": str(out_path)}


def build_graph():
    """Construct the supervisor graph: discovery → 5 parallel sub-agents → synthesize."""
    g = StateGraph(AnalyzerState)
    g.add_node("discovery", discovery_node)
    g.add_node("onchain", onchain_node)
    g.add_node("tokenomics", tokenomics_node)
    g.add_node("sentiment", sentiment_node)
    g.add_node("technical", technical_node)
    g.add_node("fundamental", fundamental_node)
    g.add_node("synthesize", synthesizer_node)

    g.add_edge(START, "discovery")
    for sub in ("onchain", "tokenomics", "sentiment", "technical", "fundamental"):
        g.add_edge("discovery", sub)
        g.add_edge(sub, "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()
