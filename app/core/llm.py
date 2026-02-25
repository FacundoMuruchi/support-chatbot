"""
Instancia compartida del LLM (OpenRouter).

Todos los nodos del grafo importan el LLM desde acá
en vez de crear su propia instancia.

Dos variantes:
- llm: temperatura 0.3, para respuestas naturales (info_agent, format_review)
- llm_strict: temperatura 0, para clasificación y tool calling (triage, support_agent)
"""

from langchain_openai import ChatOpenAI

from app.core.config import settings

llm = ChatOpenAI(
    model="arcee-ai/trinity-large-preview:free",
    openai_api_key=settings.openrouter_api_key,
    openai_api_base=settings.openrouter_base_url,
    temperature=0.3,
)

llm_strict = ChatOpenAI(
    model="arcee-ai/trinity-large-preview:free",
    openai_api_key=settings.openrouter_api_key,
    openai_api_base=settings.openrouter_base_url,
    temperature=0,
)

llm_format = ChatOpenAI(
    model="nvidia/nemotron-3-nano-30b-a3b:free",
    openai_api_key=settings.openrouter_api_key,
    openai_api_base=settings.openrouter_base_url,
    temperature=0,
)
