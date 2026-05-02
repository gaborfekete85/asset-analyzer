"""Provider-agnostic LLM factory.

Model strings use LangChain's `init_chat_model` convention:

    "anthropic:claude-sonnet-4-6"
    "openai:gpt-4o-mini"
    "openai:gpt-4o"
    "google_genai:gemini-2.0-flash"
    "ollama:llama3.1"

Defaults can be overridden per-role via env vars:

    ANALYZER_DISCOVERY_MODEL
    ANALYZER_SUBAGENT_MODEL
    ANALYZER_SYNTHESIS_MODEL

Or a single fallback for all three:

    ANALYZER_MODEL
"""

from __future__ import annotations

import os
from typing import Literal

from langchain.chat_models import init_chat_model

Role = Literal["discovery", "subagent", "synthesis"]

_DEFAULTS: dict[Role, str] = {
    "discovery": "anthropic:claude-sonnet-4-6",
    "subagent": "anthropic:claude-sonnet-4-6",
    "synthesis": "anthropic:claude-opus-4-7",
}

_ROLE_MAX_TOKENS: dict[Role, int] = {
    "discovery": 4000,
    "subagent": 8000,
    "synthesis": 16000,
}


def _model_for(role: Role) -> str:
    return (
        os.environ.get(f"ANALYZER_{role.upper()}_MODEL")
        or os.environ.get("ANALYZER_MODEL")
        or _DEFAULTS[role]
    )


def get_llm(role: Role):
    """Build a chat model for the given role.

    `init_chat_model` infers the right LangChain provider package from the
    `provider:model` prefix and applies provider-specific kwargs that
    don't apply elsewhere are silently dropped.
    """
    model = _model_for(role)
    return init_chat_model(model, max_tokens=_ROLE_MAX_TOKENS[role])
