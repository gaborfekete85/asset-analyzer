import os


def get_search_tool():
    """Return a Tavily search tool. Requires TAVILY_API_KEY."""
    if not os.environ.get("TAVILY_API_KEY"):
        raise RuntimeError(
            "TAVILY_API_KEY not set. Get a free key at https://tavily.com and "
            "export it before running the analyzer."
        )
    try:
        from langchain_tavily import TavilySearch

        return TavilySearch(max_results=5, topic="general")
    except ImportError:
        from langchain_community.tools.tavily_search import TavilySearchResults

        return TavilySearchResults(max_results=5)
