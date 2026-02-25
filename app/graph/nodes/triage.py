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

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.llm import llm_strict as llm
from app.graph.state import SupportState

# ── Prompt del clasificador ─────────────────────────────────────
TRIAGE_SYSTEM_PROMPT = """Eres un clasificador de intenciones para FM.inc, una empresa de telefonía móvil.

Tu ÚNICA tarea es clasificar el mensaje del usuario en UNA de estas dos categorías:

1. "info" — El usuario pregunta sobre:
   - Planes de telefonía (precios, datos, beneficios)
   - Cobertura y zonas de servicio
   - Beneficios y promociones
   - Información general de la empresa

2. "soporte" — El usuario quiere:
   - Reportar un problema técnico o avería
   - Consultar el estado de un ticket existente
   - Ver sus tickets anteriores
   - Reportar fallas de señal, internet, facturación, equipo

REGLAS:
- Responde ÚNICAMENTE con la palabra "info" o "soporte" (sin comillas, sin explicación).
- Si no estás seguro, clasifica como "info".
- No generes ningún otro texto.
"""


async def triage_node(state: SupportState) -> dict:
    """
    Nodo de triaje: clasifica el intent del último mensaje.

    Recibe el state completo, extrae el último mensaje del usuario,
    y retorna {"intent": "info" | "soporte"}.

    Este retorno se MERGEA con el state existente (no lo reemplaza).
    """
    # Obtener el último mensaje del usuario
    last_message = state["messages"][-1]

    # Llamar al LLM para clasificar
    response = await llm.ainvoke([
        SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
        HumanMessage(content=last_message.content),
    ])

    # Limpiar la respuesta (por si el LLM agrega espacios o saltos de línea)
    intent = response.content.strip().lower()

    # Validar que sea un intent conocido
    if intent not in ("info", "soporte"):
        intent = "info"  # fallback seguro

    print(f"🔀 Triaje: intent clasificado como '{intent}'")

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
