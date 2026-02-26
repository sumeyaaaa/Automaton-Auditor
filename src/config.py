"""
Configuration management for Automaton Auditor.
Provides model factory and environment variable loading.

DeepSeek compatibility notes:
─────────────────────────────
• MUST use langchain-deepseek (ChatDeepSeek), NOT ChatOpenAI with base_url.
  ChatOpenAI sends response_format=json_schema which DeepSeek rejects (HTTP 400).
• Use deepseek-chat (V3.2 non-thinking). deepseek-reasoner (R1) has known
  structured-output bugs (open LangChain issue).
• Structured output in judges.py must use method="function_calling":
      llm.with_structured_output(Model, method="function_calling")
"""
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from src.exceptions import (
    InvalidLayerError,
    MissingAPIKeyError,
    UnsupportedProviderError,
)

logger = logging.getLogger(__name__)

# ── Optional provider imports ────────────────────────────────
# Each is optional; we check HAS_* flags at call time.

try:
    from langchain_groq import ChatGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

try:
    from langchain_xai import ChatXAI
    HAS_XAI = True
except ImportError:
    HAS_XAI = False
    ChatXAI = None

# OpenAI — needed as its own provider AND as xAI fallback.
# Imported unconditionally so the xai branch always has it.
try:
    from langchain_openai import ChatOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    ChatOpenAI = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    HAS_GOOGLE = True
except ImportError:
    try:
        from langchain_google_vertexai import ChatVertexAI
        HAS_GOOGLE = True
        ChatGoogleGenerativeAI = ChatVertexAI
    except ImportError:
        HAS_GOOGLE = False

try:
    from langchain_deepseek import ChatDeepSeek
    HAS_DEEPSEEK = True
except ImportError:
    HAS_DEEPSEEK = False
    ChatDeepSeek = None

# ── Load .env once at import time ────────────────────────────
load_dotenv()

# ── Model config — built once, reused everywhere ────────────
# All layers default to DeepSeek for cost efficiency
# ($0.28/$0.42 per 1M tokens; cache hits drop input to $0.028).
#
# Override any layer via env vars:
#   LAYER2_PROVIDER=xai  LAYER2_MODEL=grok-4-fast  XAI_API_KEY=...

MODEL_CONFIG: dict[str, dict[str, str]] = {
    "investigator": {
        "model": os.getenv("INVESTIGATOR_MODEL", "deepseek-chat"),
        "provider": os.getenv("INVESTIGATOR_PROVIDER", "deepseek"),
    },
    "layer1": {
        "model": os.getenv("LAYER1_MODEL", "deepseek-chat"),
        "provider": os.getenv("LAYER1_PROVIDER", "deepseek"),
    },
    "layer2": {
        "model": os.getenv("LAYER2_MODEL", "deepseek-chat"),
        "provider": os.getenv("LAYER2_PROVIDER", "deepseek"),
    },
    "layer3": {
        "model": os.getenv("LAYER3_MODEL", "deepseek-chat"),
        "provider": os.getenv("LAYER3_PROVIDER", "deepseek"),
    },
    "visual": {
        "model": os.getenv("VISUAL_MODEL", "deepseek-chat"),
        "provider": os.getenv("VISUAL_PROVIDER", "deepseek"),
    },
}

VALID_LAYERS: list[str] = list(MODEL_CONFIG.keys())
SUPPORTED_PROVIDERS: list[str] = ["deepseek", "xai", "groq", "google"]


def get_llm(layer: str, temperature: float = 0) -> BaseChatModel:
    """Get configured LLM instance for a specific layer.

    Args:
        layer: "investigator", "layer1", "layer2", "layer3", or "visual"
        temperature: Default 0 for deterministic scoring.
                     Pass higher values explicitly for creative tasks.

    Returns:
        Configured LLM instance ready for .invoke() or .with_structured_output().

    Raises:
        InvalidLayerError: Unknown layer name
        MissingAPIKeyError: Required API key not in environment
        UnsupportedProviderError: Provider package not installed
    """
    if layer not in MODEL_CONFIG:
        raise InvalidLayerError(layer, VALID_LAYERS)

    config = MODEL_CONFIG[layer]
    provider = config["provider"]
    model = config["model"]

    # ── DeepSeek (default for all layers) ────────────────────
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("DEEPSEEK_API_KEY")

        if not HAS_DEEPSEEK:
            raise UnsupportedProviderError(
                "deepseek",
                SUPPORTED_PROVIDERS,
            )

        # Warn if someone configures deepseek-reasoner — structured output is broken
        if model == "deepseek-reasoner":
            logger.warning(
                "deepseek-reasoner (R1) has known bugs with .with_structured_output(). "
                "Use deepseek-chat instead for reliable structured output."
            )

        return ChatDeepSeek(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )

    # ── xAI / Grok ──────────────────────────────────────────
    elif provider == "xai":
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("XAI_API_KEY")

        if HAS_XAI:
            return ChatXAI(
                model=model,
                temperature=temperature,
                api_key=api_key,
            )
        elif HAS_OPENAI:
            # Fallback: xAI exposes an OpenAI-compatible endpoint
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=api_key,
                base_url="https://api.x.ai/v1",
            )
        else:
            raise UnsupportedProviderError("xai", SUPPORTED_PROVIDERS)

    # ── Groq (Llama) ────────────────────────────────────────
    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("GROQ_API_KEY")

        if not HAS_GROQ:
            raise UnsupportedProviderError("groq", SUPPORTED_PROVIDERS)

        return ChatGroq(
            model=model,
            temperature=temperature,
            groq_api_key=api_key,
        )

    # ── Google Gemini ────────────────────────────────────────
    elif provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("GOOGLE_API_KEY")

        if not HAS_GOOGLE:
            raise UnsupportedProviderError("google", SUPPORTED_PROVIDERS)

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
        )

    else:
        raise UnsupportedProviderError(provider, SUPPORTED_PROVIDERS)


# ── Metadata helpers ─────────────────────────────────────────

def get_model_metadata() -> dict[str, dict[str, str]]:
    """Return metadata about configured models for audit report reproducibility."""
    return MODEL_CONFIG.copy()


def is_langsmith_enabled() -> bool:
    """Check if LangSmith tracing is enabled."""
    return os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"


def get_langsmith_project() -> Optional[str]:
    """Get LangSmith project name from environment."""
    return os.getenv("LANGCHAIN_PROJECT")