"""
Instancia compartida del LLM (OpenRouter).

Todos los nodos del grafo importan el LLM desde acá
en vez de crear su propia instancia.

Tres variantes:
- llm: temperatura 0.3, para respuestas naturales (info_agent)
- llm_strict: temperatura 0, para clasificación y tool calling (triage, support_agent)
- llm_format: modelo rápido para formato y resumen

Retry: todas las instancias tienen retry automático con backoff exponencial
para manejar rate limits de modelos free en OpenRouter (error 429).
"""

import logging

from langchain_openai import ChatOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


def _create_llm(model: str, temperature: float) -> ChatOpenAI:
    """Crea una instancia de ChatOpenAI con configuración compartida."""
    return ChatOpenAI(
        model=model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        temperature=temperature,
    )


# ── Instancias ──
llm = _create_llm("arcee-ai/trinity-large-preview:free", temperature=0.3)
llm_strict = _create_llm("arcee-ai/trinity-large-preview:free", temperature=0)
llm_format = _create_llm("nvidia/nemotron-3-nano-30b-a3b:free", temperature=0.5)


# ── Retry wrapper ──
@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(3),
    before_sleep=lambda retry_state: logger.warning(
        f"⏳ LLM rate limited, reintentando en {retry_state.next_action.sleep:.0f}s... "
        f"(intento {retry_state.attempt_number}/3)"
    ),
)
async def invoke_with_retry(llm_instance, messages):
    """
    Llama al LLM con retry automático y backoff exponencial.
    Maneja errores 429 (rate limit) de modelos free en OpenRouter.
    """
    return await llm_instance.ainvoke(messages)
