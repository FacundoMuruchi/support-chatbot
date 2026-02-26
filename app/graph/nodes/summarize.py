"""
Nodo de resumen de conversación.

Cuando el historial supera un límite de mensajes, este nodo:
1. Resume los mensajes conversacionales (ignora tool calls internas)
2. Borra los mensajes viejos del state (con RemoveMessage)
3. Mantiene solo los 2 más recientes

Así la conversación nunca crece sin límite, pero el contexto
importante se preserva en el resumen.
"""

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from app.core.llm import invoke_with_retry, llm_format as llm
from app.graph.state import SupportState

# Cantidad de mensajes conversacionales antes de activar el resumen
MAX_MESSAGES = 6


def _get_conversation_messages(messages):
    """
    Filtra solo los mensajes conversacionales:
    - HumanMessage (lo que dice el usuario)
    - AIMessage SIN tool_calls (respuestas finales del bot)

    Ignora AIMessage con tool_calls y ToolMessage (internas del ReAct loop).
    """
    return [
        m for m in messages
        if isinstance(m, HumanMessage)
        or (isinstance(m, AIMessage) and not m.tool_calls)
    ]


async def should_summarize(state: SupportState) -> str:
    """
    Después de format_review, decidir si hay que resumir.
    Cuenta solo mensajes conversacionales (no tool calls internas).
    """
    conversation_msgs = _get_conversation_messages(state["messages"])
    if len(conversation_msgs) > MAX_MESSAGES:
        return "summarize_conversation"
    return "__end__"


async def summarize_conversation(state: SupportState) -> dict:
    """
    Resumir los mensajes viejos y borrarlos del state.
    Solo envía mensajes conversacionales al LLM para resumir.
    Mantiene los 2 últimos mensajes del state intactos.
    """
    summary = state.get("summary", "")

    # Filtrar solo mensajes conversacionales para el resumen
    conversation_msgs = _get_conversation_messages(state["messages"])

    if summary:
        summary_prompt = (
            f"Este es el resumen sobre el usuario hasta ahora: {summary}\n\n"
            "Reescribe el resumen de forma breve y concisa teniendo en cuenta los mensajes nuevos de arriba."
        )
    else:
        summary_prompt = (
            "Creá un resumen breve y conciso acerca del usuario usando la conversación de arriba."
        )

    messages = conversation_msgs + [HumanMessage(content=summary_prompt)]
    response = await invoke_with_retry(llm, messages)

    # Borrar TODOS los mensajes viejos (incluyendo tool calls), dejar los 2 últimos
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]

    return {"summary": response.content, "messages": delete_messages}
