"""Multi-agent LangGraph crypto analyzer.

Submodules are intentionally imported lazily so that simply importing
`analyzer` does not pull in the heavy `langchain_anthropic` /
`langgraph` deps unless you actually build the graph.
"""

__all__ = ["build_graph"]


def __getattr__(name):
    if name == "build_graph":
        from .supervisor import build_graph

        return build_graph
    raise AttributeError(name)
