"""
Estado compartido del grafo LangGraph.

Hereda de MessagesState, que incluye el campo `messages`
con el reducer add_messages (acumula mensajes en vez de reemplazarlos).

Los campos adicionales (user_phone, intent, context, response)
se definen en SupportState y viajan entre todos los nodos.
"""

from langgraph.graph import MessagesState


class SupportState(MessagesState):
    """
    Estado compartido entre todos los nodos del grafo.

    Campos:

        user_phone: Número de WhatsApp del usuario (ej: "5491112345678").
                    Se extrae del webhook de WhatsApp.

        intent: Clasificación del mensaje por el nodo de triaje.
                Valores: "info" | "soporte" | "" (vacío = no clasificado).

        context: Documentos recuperados de Pinecone (RAG).
                 Solo se llena cuando intent == "info".

        response: Respuesta para WhatsApp. Se llena en info_agent o
                  support_agent, y luego format_review la sobreescribe
                  con el formato final (emojis, negritas, etc.).

        summary: Resumen de la conversación anterior. Se genera cuando
                 el historial es largo y se inyecta como SystemMessage.
    """
    user_phone: str
    intent: str
    context: str
    response: str
    summary: str