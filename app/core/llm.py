"""
Instancia compartida del LLM (OpenRouter).

Todos los nodos del grafo importan el LLM desde acá
en vez de crear su propia instancia.

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

# ── Instancias ──
llm = ChatOpenAI(
        model="openai/gpt-oss-120b:free",
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        temperature=0,
    )

tono_negocio = (
    "Usá un tono amigable, cercano y profesional. "
    "Hablá siempre de 'vos' (español rioplatense). "
    "Sé conciso, breve y directo. "
    "Usá emojis con moderación para hacer el mensaje más cálido. "
    "Nunca uses tablas, recuerda que estas no se muestran correctamente en WhatsApp. "
)

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
