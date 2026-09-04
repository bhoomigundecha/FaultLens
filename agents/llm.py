"""
FaultLens LLM Provider Factory.

Provides a unified interface for agent nodes to obtain chat models, supporting:
  - Groq Cloud (ultra-fast LPU inference, zero local CPU load)
  - Ollama (local fallback for offline development)
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_model_cache: dict[tuple[str, str, float], BaseChatModel] = {}


def get_chat_llm(temperature: float = 0.1, **kwargs: Any) -> BaseChatModel:
    """
    Get a configured chat model instance based on settings.llm_provider.

    Args:
        temperature: Sampling temperature for the model.
        **kwargs: Additional provider-specific kwargs.

    Returns:
        BaseChatModel instance (ChatGroq or ChatOllama).
    """
    provider = (settings.llm_provider or "groq").lower().strip()

    if provider == "groq":
        if not settings.groq_api_key:
            logger.warning(
                "[LLM] GROQ_API_KEY is not set. Falling back to local Ollama."
            )
            return _get_ollama_llm(temperature=temperature, **kwargs)

        cache_key = ("groq", settings.groq_model, temperature)
        if cache_key not in _model_cache:
            try:
                from langchain_groq import ChatGroq

                logger.info(
                    f"[LLM] Initializing ChatGroq with model={settings.groq_model}, temp={temperature}"
                )
                _model_cache[cache_key] = ChatGroq(
                    model=settings.groq_model,
                    api_key=settings.groq_api_key,
                    temperature=temperature,
                    **kwargs,
                )
            except Exception as e:
                logger.error(f"[LLM] Failed to initialize ChatGroq: {e}. Falling back to Ollama.")
                return _get_ollama_llm(temperature=temperature, **kwargs)

        return _model_cache[cache_key]

    return _get_ollama_llm(temperature=temperature, **kwargs)


def _get_ollama_llm(temperature: float = 0.1, **kwargs: Any) -> BaseChatModel:
    """Create or retrieve a cached ChatOllama instance."""
    from langchain_ollama import ChatOllama

    cache_key = ("ollama", settings.ollama_model, temperature)
    if cache_key not in _model_cache:
        logger.info(
            f"[LLM] Initializing ChatOllama with model={settings.ollama_model}, "
            f"base_url={settings.ollama_base_url}, temp={temperature}"
        )
        _model_cache[cache_key] = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            **kwargs,
        )
    return _model_cache[cache_key]
