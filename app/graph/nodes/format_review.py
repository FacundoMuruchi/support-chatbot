"""
Nodo de Revisión de Formato.

Último nodo del grafo. Toma la respuesta raw de los agentes y la
adapta para el formato de WhatsApp.

Conceptos clave para aprender:
- Este nodo es un "post-procesador": no genera contenido nuevo,
  sino que transforma la respuesta existente.
- Es importante porque WhatsApp tiene limitaciones de formato
  (no soporta markdown completo, tiene límite de caracteres, etc.)
"""

import logging

from langchain_core.messages import AIMessage, SystemMessage

logger = logging.getLogger(__name__)

from app.core.llm import invoke_with_retry, llm_format as llm
from app.graph.state import SupportState

MAX_WHATSAPP_CHARS = 1000

FORMAT_SYSTEM_PROMPT = """Eres un formateador de mensajes para WhatsApp de FM.inc.

Tu tarea es tomar la respuesta del agente y adaptarla para WhatsApp.

REGLAS DE FORMATO:
1. Máximo 1000 caracteres.
2. Usa emojis apropiados para hacer el mensaje amigable (📱, ✅, 📋, 💰, 🌐, etc.)
3. No uses markdown (no **, no ##, no ```). WhatsApp usa *negrita* y _cursiva_.
4. Usa saltos de línea para separar secciones.
5. Si hay una lista, usa emojis como bullets (• o ▸).
6. Termina con un mensaje amigable como "¿Te puedo ayudar en algo más? 😊"
7. Mantén un tono profesional pero cercano.
8. Si la respuesta original es corta, no la alargues innecesariamente.

IMPORTANTE: Devolvé SOLO el mensaje formateado, sin explicaciones.
"""


async def format_review_node(state: SupportState) -> dict:
    """
    Nodo de formato: adapta la respuesta para WhatsApp.

    Toma state["response"] (la respuesta raw del agente) y la
    pasa por el LLM para formatearla según las reglas de WhatsApp.

    Retorna el response formateado y lo agrega a messages.
    """
    # Obtener respuesta: primero de state["response"], si no del último AIMessage
    raw_response = state.get("response", "")
    if not raw_response:
        # Buscar el último AIMessage en el historial (patrón ToolNode)
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                raw_response = msg.content
                break

    if not raw_response:
        formatted = "😅 Disculpá, no pude procesar tu mensaje. ¿Podrías intentar de nuevo?"
    else:
        try:
            result = await invoke_with_retry(llm, [
                SystemMessage(content=FORMAT_SYSTEM_PROMPT),
                SystemMessage(content=f"RESPUESTA ORIGINAL:\n{raw_response}"),
            ])
            formatted = result.content.strip()
        except Exception as e:
            logger.error(f"❌ Error formateando respuesta: {e}")
            formatted = raw_response  # Fallback: enviar sin formatear

    # Asegurar límite de caracteres
    if len(formatted) > MAX_WHATSAPP_CHARS:
        formatted = formatted[:MAX_WHATSAPP_CHARS - 3] + "..."

    logger.info(f"📝 Format Review: respuesta formateada ({len(formatted)} chars)")

    return {
        "response": formatted,
    }
