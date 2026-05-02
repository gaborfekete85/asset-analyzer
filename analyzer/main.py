"""CLI entry point.

Usage:
    python -m analyzer.main BTC
    python -m analyzer.main --check        # diagnose config, no graph run
    python -m analyzer.main solana
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv


def _mask(val: str | None) -> str:
    if not val:
        return "(unset)"
    return f"{val[:8]}…{val[-4:]} ({len(val)} chars)"


def _check() -> int:
    """Print resolved config and ping each role's model with a 1-token call."""
    from langchain_core.messages import HumanMessage

    from .llm import _model_for, get_llm

    print("=== Environment ===", file=sys.stderr)
    print(f"  ANTHROPIC_API_KEY = {_mask(os.environ.get('ANTHROPIC_API_KEY'))}", file=sys.stderr)
    print(f"  OPENAI_API_KEY    = {_mask(os.environ.get('OPENAI_API_KEY'))}", file=sys.stderr)
    print(f"  TAVILY_API_KEY    = {_mask(os.environ.get('TAVILY_API_KEY'))}", file=sys.stderr)
    print(file=sys.stderr)
    print("=== Resolved models ===", file=sys.stderr)
    for role in ("discovery", "subagent", "synthesis"):
        print(f"  {role:10s} = {_model_for(role)}", file=sys.stderr)
    print(file=sys.stderr)

    print("=== Ping each role's model ===", file=sys.stderr)
    failures = 0
    for role in ("discovery", "subagent", "synthesis"):
        try:
            llm = get_llm(role)
            resp = llm.invoke([HumanMessage(content="Reply with the single word: pong")])
            text = resp.content if isinstance(resp.content, str) else str(resp.content)[:60]
            print(f"  [OK]  {role:10s} -> {text!r}", file=sys.stderr)
        except Exception as exc:
            failures += 1
            print(f"  [FAIL] {role:10s} -> {type(exc).__name__}: {exc}", file=sys.stderr)
    print(file=sys.stderr)
    return 0 if failures == 0 else 2


def _draw_graph(path: str) -> int:
    """Render the compiled graph topology to a PNG and dump mermaid text."""
    from pathlib import Path

    from .supervisor import build_graph

    graph = build_graph().get_graph()

    mermaid_src = graph.draw_mermaid()
    print("=== Mermaid source ===", file=sys.stderr)
    print(mermaid_src, file=sys.stderr)

    out = Path(path)
    try:
        png_bytes = graph.draw_mermaid_png()
    except Exception as exc:
        print(
            f"\n[asset-analyzer] PNG rendering failed ({type(exc).__name__}: {exc}).",
            file=sys.stderr,
        )
        print(
            "Mermaid source above can be pasted into https://mermaid.live to view.",
            file=sys.stderr,
        )
        return 1

    out.write_bytes(png_bytes)
    print(f"\n[asset-analyzer] Graph PNG written to: {out.resolve()}", file=sys.stderr)
    return 0


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Multi-agent LangGraph crypto analyzer (mirrors the Claude-Code skill set)."
    )
    parser.add_argument(
        "symbol",
        nargs="?",
        help="Token ticker, name, slug, or contract address (e.g. BTC, Ethereum, solana).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Diagnose: print resolved models and ping each. Skips the graph run.",
    )
    parser.add_argument(
        "--graph",
        nargs="?",
        const="graph.png",
        metavar="PATH",
        help="Render the LangGraph topology to PATH (default: graph.png) and exit.",
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Only write the report to disk; do not echo to stdout.",
    )
    args = parser.parse_args()

    if args.check:
        return _check()

    if args.graph is not None:
        return _draw_graph(args.graph)

    if not args.symbol:
        parser.error("symbol is required (or pass --check / --graph)")

    from .supervisor import build_graph

    graph = build_graph()
    print(f"[asset-analyzer] Running multi-agent analysis for: {args.symbol}", file=sys.stderr)
    final_state = graph.invoke({"symbol": args.symbol})

    print(f"[asset-analyzer] Report saved to: {final_state['output_path']}", file=sys.stderr)
    if not args.no_print:
        print(final_state["final_report"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
