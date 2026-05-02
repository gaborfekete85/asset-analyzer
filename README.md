# Asset Analyzer (LangGraph)

LangGraph implementation of the multi-agent crypto analysis system whose
original Claude-Code skill definitions live in `skills/`.

The graph mirrors the Claude-Code orchestration: a supervisor resolves the
token, then fans out to 5 specialist sub-agents in parallel, then a
synthesizer joins their reports into a single composite-scored markdown
deliverable.

## Architecture

```
              ┌──────────────┐
  symbol ───▶ │  discovery   │  resolves ticker → token profile
              └──────┬───────┘
                     │  (parallel fan-out)
   ┌────────┬────────┼────────┬─────────┐
   ▼        ▼        ▼        ▼         ▼
 onchain tokenomics sentiment technical fundamental    (each = create_react_agent
   │        │        │         │         │              with its SKILL.md as prompt)
   └────────┴────┬───┴─────────┴─────────┘
                 ▼
          ┌──────────────┐
          │  synthesize  │  composite score + final markdown
          └──────┬───────┘
                 ▼
       reports/CRYPTO-ANALYSIS-<TICKER>.md
```

### Mapping to the Claude-Code design

| Claude-Code concept           | LangGraph equivalent                                  |
|-------------------------------|--------------------------------------------------------|
| Main `crypto-analyze` skill   | `discovery_node` + `synthesizer_node` in `supervisor.py` |
| 5 sub-agent skills            | 5 nodes in `sub_agents.py`, each a `create_react_agent` |
| Markdown skill files          | Loaded verbatim by `prompts.py` as the agent's system prompt |
| Skill selection               | Static fan-out edges in `build_graph()`               |
| Skill execution               | Subagent node invocation                              |
| `WebSearch` tool              | `langchain_tavily.TavilySearch`                       |
| Final `.md` artifact          | `reports/CRYPTO-ANALYSIS-<TICKER>.md`                 |

## Setup

```bash
cd svcs/asset-analyzer
python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env
# Fill in ANTHROPIC_API_KEY and TAVILY_API_KEY in .env
```

Tavily gives you 1,000 free searches/month — plenty for testing
([tavily.com](https://tavily.com)).

## Run

```bash
python -m analyzer.main BTC
python -m analyzer.main "Ethereum"
python -m analyzer.main solana
python -m analyzer.main ARB
```

Or using the installed entry point:

```bash
asset-analyzer BTC
```

The full report streams to stdout and is written to
`reports/CRYPTO-ANALYSIS-<TICKER>.md`.

## How the skills become prompts

`analyzer/prompts.py` reads each `SKILL.md`, strips the YAML frontmatter,
and appends a short adaptation block telling the agent:

1. Use the `tavily_search` tool wherever the skill says `WebSearch:`.
2. Don't write a file — emit the markdown report as the final message.
3. Don't try to delegate (the skill's "Use the Agent tool" snippets are
   moot inside a single LangGraph node).

This keeps the markdown skills as the **single source of truth** — to
tweak an agent's behavior, edit the corresponding `SKILL.md` and re-run.

## File layout

```
svcs/asset-analyzer/
├── pyproject.toml
├── .env.example
├── README.md
├── analyzer/
│   ├── __init__.py
│   ├── state.py        # AnalyzerState TypedDict
│   ├── prompts.py      # SKILL.md loaders + prompt templates
│   ├── tools.py        # Tavily search tool
│   ├── sub_agents.py   # 5 react-agent nodes
│   ├── supervisor.py   # discovery + synthesizer + graph
│   └── main.py         # CLI
├── skills/             # Source-of-truth markdown skills
│   ├── crypto-analyze/SKILL.md
│   └── sub-agents/
│       ├── crypto-onchain/SKILL.md
│       ├── crypto-tokenomics/SKILL.md
│       ├── crypto-sentiment/SKILL.md
│       ├── crypto-technical/SKILL.md
│       └── crypto-fundamental/SKILL.md
└── reports/            # Generated CRYPTO-ANALYSIS-*.md files
```

## Switching LLM providers

Models use LangChain's `provider:model` convention via
`init_chat_model`, so you can swap providers without code changes.

| Env var                       | Default                          | Purpose                       |
|-------------------------------|----------------------------------|-------------------------------|
| `ANALYZER_MODEL`              | (unset)                          | Single override for all roles |
| `ANALYZER_DISCOVERY_MODEL`    | `anthropic:claude-sonnet-4-6`    | Token resolution              |
| `ANALYZER_SUBAGENT_MODEL`     | `anthropic:claude-sonnet-4-6`    | Each of the 5 sub-agents      |
| `ANALYZER_SYNTHESIS_MODEL`    | `anthropic:claude-opus-4-7`      | Final synthesis               |
| `ANALYZER_REPORTS_DIR`        | `reports`                        | Output directory              |

### Run on OpenAI instead of Anthropic

```bash
unset ANTHROPIC_API_KEY      # not needed
export OPENAI_API_KEY=sk-...
export ANALYZER_DISCOVERY_MODEL=openai:gpt-4o-mini
export ANALYZER_SUBAGENT_MODEL=openai:gpt-4o-mini
export ANALYZER_SYNTHESIS_MODEL=openai:gpt-4o

python -m analyzer.main BTC
```

### Other supported prefixes

- `anthropic:claude-sonnet-4-6`, `anthropic:claude-opus-4-7`, `anthropic:claude-haiku-4-5`
- `openai:gpt-4o`, `openai:gpt-4o-mini`, `openai:gpt-4-turbo`
- `google_genai:gemini-2.0-flash` *(install `langchain-google-genai`)*
- `ollama:llama3.1` *(install `langchain-ollama`, run a local Ollama server)*

To swap the search backend, edit `analyzer/tools.py`. Any LangChain tool
implementing the `BaseTool` interface works.

## Cost note

A full Anthropic run (Sonnet sub-agents + Opus synthesis) costs roughly
$1–3 per token analyzed. The cheap-OpenAI preset above costs roughly
$0.05–0.15 per run — useful for iteration.

## Disclaimer

For educational/research purposes only. Not financial advice.
Cryptocurrency is highly volatile. Always DYOR.
