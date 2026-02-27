"""
Nodo de Triaje (Router).

Primer nodo del grafo. Analiza el mensaje del usuario y clasifica
su intención en una de dos categorías:
  - "info": preguntas sobre planes, cobertura, beneficios, precios
  - "soporte": reportar averías, consultar tickets, problemas técnicos

Conceptos clave para aprender:
- Este nodo es un ROUTER: no genera la respuesta final, solo decide
  el camino que tomará el grafo.
- Usa el LLM para clasificar (más robusto que keywords).
- El resultado se usa en add_conditional_edges para enrutar.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

from app.core.llm import invoke_with_retry, llm
from app.graph.state import SupportState

# ── Prompt del clasificador ─────────────────────────────────────
TRIAGE_SYSTEM_PROMPT = """Eres un clasificador de intenciones para FM.inc, una empresa de telefonía móvil.

Tu ÚNICA tarea es analizar la conversación y clasificar la intención del ÚLTIMO mensaje del usuario en UNA de estas dos categorías:

1. "info" — El usuario está pidiendo información general sobre precios, planes de telefonía, cobertura comercial, beneficios o promociones.

2. "soporte" — El usuario está reportando un problema técnico, o quiere consultar, ver o gestionar sus tickets de soporte, o está en medio de una conversación técnica respondiendo a preguntas del agente.

REGLAS VITALES Y ESTRICTAS:
- Si el usuario menciona la palabra "ticket", "tickets" o "estado", la intención es SIEMPRE "soporte". NUNCA "info".
- Si el usuario dice "quiero ver mis tickets", "mis tickets", "estado de mi ticket" la intención es SIEMPRE "soporte".
- Si el contexto de la conversación previa demuestra que el usuario está reportando o detallando una falla técnica actualmente en curso, SIEMPRE clasifica su último mensaje como "soporte", por más corto o ambiguo que parezca en aislamiento.
- Responde ÚNICAMENTE con la palabra "info" o "soporte" (sin comillas, sin explicación).
- Si es la primera interacción y es un saludo genérico ("hola"), clasifica como "info".
"""


async def triage_node(state: SupportState) -> dict:
    """
    Nodo de triaje: clasifica el intent del último mensaje.

    Recibe el state completo, extrae el último mensaje del usuario,
    y retorna {"intent": "info" | "soporte"}.

    Este retorno se MERGEA con el state existente (no lo reemplaza).
    """
    # Obtener los últimos mensajes para darle contexto al router (soporta hasta 2)
    recent_messages = state["messages"][-2:]

    # Llamar al LLM para clasificar pasando la historia reciente
    messages = [SystemMessage(content=TRIAGE_SYSTEM_PROMPT)] + recent_messages
    
    response = await invoke_with_retry(llm, messages)

    # Limpiar la respuesta (por si el LLM agrega espacios o saltos de línea)
    intent = response.content.strip().lower()

    # Validar que sea un intent conocido
    if intent not in ("info", "soporte"):
        intent = "info"  # fallback seguro

    logger.info(f"🔀 Triaje: intent clasificado como '{intent}'")

    return {"intent": intent}


def route_by_intent(state: SupportState) -> str:
    """
    Función de routing para add_conditional_edges.

    LangGraph llama esta función DESPUÉS del nodo de triaje.
    El string retornado debe coincidir con las keys del dict
    de edges en graph.py.

    Ejemplo en graph.py:
        graph.add_conditional_edges("triage", route_by_intent, {
            "info": "info_agent",
            "soporte": "support_agent",
        })
    """
    return state["intent"]
