from typing import TypedDict
from typing_extensions import NotRequired


class AnalyzerState(TypedDict):
    """Shared state flowing through the supervisor graph.

    `symbol` is the only required input. Every other field is filled in
    by exactly one node, so concurrent writes from the parallel
    sub-agents never collide on the same key.
    """

    symbol: str
    token_profile: NotRequired[dict]
    onchain_report: NotRequired[str]
    tokenomics_report: NotRequired[str]
    sentiment_report: NotRequired[str]
    technical_report: NotRequired[str]
    fundamental_report: NotRequired[str]
    final_report: NotRequired[str]
    output_path: NotRequired[str]
