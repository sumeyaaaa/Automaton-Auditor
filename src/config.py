"""
Configuration management for Automaton Auditor.
Provides model factory and environment variable loading.
"""
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()


def get_llm(layer: str, temperature: float = 0.7) -> BaseChatModel:
    """Get configured LLM instance for a specific layer.
    
    Args:
        layer: Layer identifier ("layer1" for detectives, "layer2" for judges)
        temperature: Temperature setting (default 0.7, use 0 for deterministic scoring)
        
    Returns:
        Configured ChatOpenAI instance
        
    Raises:
        ValueError: If API key is missing or layer is invalid
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )
    
    # Model configuration per layer
    model_config = {
        "layer1": {
            "model": os.getenv("LAYER1_MODEL", "gpt-4o-mini"),
            "provider": os.getenv("LAYER1_PROVIDER", "openai"),
        },
        "layer2": {
            "model": os.getenv("LAYER2_MODEL", "gpt-4o"),
            "provider": os.getenv("LAYER2_PROVIDER", "openai"),
        },
        "layer3": {
            "model": os.getenv("LAYER3_MODEL", "gpt-4o"),
            "provider": os.getenv("LAYER3_PROVIDER", "openai"),
        },
    }
    
    if layer not in model_config:
        raise ValueError(
            f"Invalid layer: {layer}. Must be one of: {list(model_config.keys())}"
        )
    
    config = model_config[layer]
    provider = config["provider"]
    model = config["model"]
    
    if provider == "openai":
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )
    else:
        raise ValueError(
            f"Provider '{provider}' not yet supported. "
            "Currently only 'openai' is supported."
        )


def get_model_metadata() -> dict:
    """Get metadata about configured models.
    
    Returns:
        Dictionary with model information for each layer
    """
    return {
        "layer1": {
            "model": os.getenv("LAYER1_MODEL", "gpt-4o-mini"),
            "provider": os.getenv("LAYER1_PROVIDER", "openai"),
        },
        "layer2": {
            "model": os.getenv("LAYER2_MODEL", "gpt-4o"),
            "provider": os.getenv("LAYER2_PROVIDER", "openai"),
        },
        "layer3": {
            "model": os.getenv("LAYER3_MODEL", "gpt-4o"),
            "provider": os.getenv("LAYER3_PROVIDER", "openai"),
        },
    }


def is_langsmith_enabled() -> bool:
    """Check if LangSmith tracing is enabled.
    
    Returns:
        True if LANGCHAIN_TRACING_V2 is set to 'true'
    """
    return os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"


def get_langsmith_project() -> Optional[str]:
    """Get LangSmith project name from environment.
    
    Returns:
        Project name or None if not set
    """
    return os.getenv("LANGCHAIN_PROJECT")

