import json
from typing import Callable

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from .llm import get_llm
from .prompts import subagent_prompt
from .state import AnalyzerState
from .tools import get_search_tool


def _flatten_content(content) -> str:
    """LangChain message `.content` can be a str or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    return str(content)


def _build_subagent(skill_name: str):
    return create_react_agent(
        get_llm("subagent"),
        tools=[get_search_tool()],
        prompt=subagent_prompt(skill_name),
    )


def _make_node(skill_name: str, state_key: str) -> Callable[[AnalyzerState], dict]:
    """Build a graph node that runs one sub-agent and writes its report."""

    def node(state: AnalyzerState) -> dict:
        agent = _build_subagent(skill_name)
        profile = state.get("token_profile", {})
        ticker = profile.get("ticker", state["symbol"])
        name = profile.get("name", state["symbol"])
        msg = (
            f"Run the {skill_name} analysis for {ticker} ({name}).\n\n"
            f"TOKEN PROFILE:\n{json.dumps(profile, indent=2)}\n\n"
            "Begin your analysis. Remember: end with the final markdown report only."
        )
        result = agent.invoke({"messages": [HumanMessage(content=msg)]})
        report = _flatten_content(result["messages"][-1].content)
        return {state_key: report}

    node.__name__ = f"{skill_name.replace('-', '_')}_node"
    return node


onchain_node = _make_node("crypto-onchain", "onchain_report")
tokenomics_node = _make_node("crypto-tokenomics", "tokenomics_report")
sentiment_node = _make_node("crypto-sentiment", "sentiment_report")
technical_node = _make_node("crypto-technical", "technical_report")
fundamental_node = _make_node("crypto-fundamental", "fundamental_report")
