from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"


def load_skill(rel_path: str) -> str:
    """Load a SKILL.md file and strip the YAML frontmatter."""
    text = (SKILLS_ROOT / rel_path).read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    return text.strip()


ADAPTATION_NOTE = """
## RUNTIME ADAPTATIONS (LangGraph execution)

You are running inside a LangGraph workflow, not Claude Code. Adapt:

1. Tool: Use the `tavily_search` tool for every "WebSearch:" query in the skill above.
2. Output: Do NOT write any file. Your FINAL message must be the complete markdown report following the OUTPUT FORMAT section above, and nothing else.
3. No delegation: Do not try to use any "Agent" tool — perform the analysis yourself.
4. Search budget: Issue between 4 and 8 search queries, then produce the final report and stop.
5. Token profile: A baseline token profile is supplied in the user message — use it; you do not need to re-fetch price/mcap.
"""


def subagent_prompt(skill_name: str) -> str:
    """Return the full system prompt for a sub-agent (skill body + adaptations)."""
    body = load_skill(f"sub-agents/{skill_name}/SKILL.md")
    return f"{body}\n\n{ADAPTATION_NOTE}"


DISCOVERY_PROMPT_TEMPLATE = """You are the Discovery phase of a crypto analysis pipeline.

The user has requested analysis of: {user_input}

Use the tavily_search tool (2-3 queries) to gather the baseline token profile, e.g.:
- "<token name> <ticker> current price market cap volume 2026"
- "<token name> chain category circulating supply max supply"
- "<token name> 24h 7d 30d 90d price change rank coingecko"

Then return ONE single JSON object — no other text, no markdown fence — with these exact fields:

{{
  "ticker": "<UPPERCASE TICKER>",
  "name": "<Proper Case Name>",
  "slug": "<coingecko-slug-or-unknown>",
  "chain": "<primary chain or Unknown>",
  "category": "<one of: Layer 1, Layer 2, DeFi, AI / DePIN, Meme, RWA, Gaming / Metaverse, Infrastructure, Privacy, Stablecoin, Other>",
  "price_usd": "<current price as string>",
  "market_cap": "<formatted market cap>",
  "fdv": "<fully diluted valuation>",
  "volume_24h": "<24h volume>",
  "change_24h": "<+/- %>",
  "change_7d": "<+/- %>",
  "change_30d": "<+/- %>",
  "change_90d": "<+/- %>",
  "circulating_supply": "<value>",
  "max_supply": "<value or Unlimited>",
  "rank": "<#rank or unknown>"
}}

Use the literal string "unknown" for any field you cannot reliably determine. Do NOT invent numbers.
"""


SYNTHESIZER_PROMPT_TEMPLATE = """You are the Synthesis phase of a multi-agent crypto analysis pipeline.

Five specialist agents have already analyzed this token. Your job is to synthesize their reports into the final unified report exactly as specified by the OUTPUT FORMAT section of the orchestrator skill below.

Procedure:

1. Extract the X/100 score from each of the 5 sub-agent reports (look for the "Score: X/100" pattern in their headers).
2. Compute the composite score as the equal-weighted average of the 5 scores, rounded to the nearest integer.
3. Assign Grade and Signal per the rubric in the orchestrator skill.
4. Look for cross-dimensional convergence and divergence.
5. Produce the final markdown report. Output ONLY the markdown report itself — no preamble, no fenced code block around the whole thing, just the report content starting with the H1.

------ ORCHESTRATOR SKILL ------
{orchestrator_skill}

------ TOKEN PROFILE (from discovery) ------
{token_profile_json}

------ ON-CHAIN ANALYTICS REPORT ------
{onchain}

------ TOKENOMICS ANALYSIS REPORT ------
{tokenomics}

------ SENTIMENT ANALYSIS REPORT ------
{sentiment}

------ TECHNICAL ANALYSIS REPORT ------
{technical}

------ FUNDAMENTAL ANALYSIS REPORT ------
{fundamental}
"""
