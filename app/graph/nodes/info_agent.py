"""
Agente de Información (RAG).

Consulta Pinecone para responder preguntas sobre planes, cobertura y
beneficios de FM.inc.

Conceptos clave para aprender:
- RAG (Retrieval Augmented Generation): combinamos búsqueda semántica
  en Pinecone con generación de texto del LLM.
- El retriever busca los documentos más relevantes.
- El LLM genera una respuesta basada en esos documentos.
- Esto evita alucinaciones: el LLM solo responde con info real.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.llm import llm
from app.graph.state import SupportState
from app.rag.vectorstore import get_retriever

# ── Prompt del agente RAG ────────────────────────────────────────
RAG_SYSTEM_PROMPT = """Eres el asistente virtual de FM.inc, una empresa de telefonía móvil argentina.

Tu rol es responder preguntas sobre planes, cobertura, beneficios, medios de pago
y preguntas frecuentes. También podés mantener una conversación natural con el usuario.

CONTEXTO RECUPERADO (datos de FM.inc):
{context}

REGLAS:
1. Para preguntas sobre productos/servicios de FM.inc, usá la información del CONTEXTO.
   Si no aparece en el contexto, decí:
   "No tengo información sobre eso. Te recomiendo contactar a nuestro equipo al 0800-555-FMINC."
2. Para preguntas conversacionales (nombre, saludos, etc.), usá el historial de chat.
3. Sé amigable, conciso y profesional. Usá "vos" (español rioplatense).
4. Si mencionás precios, siempre incluí el signo $ y la moneda (ARS). Ej: $12.990 ARS/mes.
5. Si el usuario pregunta por varios planes, comparalos brevemente.
6. No inventes información, descuentos ni promociones que no estén en el contexto.
"""


async def info_agent_node(state: SupportState) -> dict:
    """
    Nodo RAG: busca en Pinecone y genera respuesta informativa.

    Flujo:
    1. Toma la query del usuario (último mensaje)
    2. Busca documentos relevantes en Pinecone (retriever)
    3. Arma el prompt con el contexto recuperado
    4. Genera respuesta con el LLM
    5. Retorna response + context en el state

    El context se guarda por si se necesita para debugging/logging.
    """
    # 1. Obtener la query del usuario (último mensaje para búsqueda)
    last_message = state["messages"][-1]
    query = last_message.content

    # 2. Recuperar documentos de Pinecone
    retriever = get_retriever(k=5)
    docs = await retriever.ainvoke(query)

    # 3. Formatear el contexto
    context = "\n\n---\n\n".join([doc.page_content for doc in docs])
    print(f"📚 Info Agent: {len(docs)} documentos recuperados de Pinecone")

    # 4. Generar respuesta con el LLM (con resumen si existe)
    summary = state.get("summary", "")
    messages = [SystemMessage(content=RAG_SYSTEM_PROMPT.format(context=context))]
    if summary:
        messages.append(SystemMessage(content=f"Resumen de la conversación anterior: {summary}"))
    messages.extend(state["messages"])

    response = await llm.ainvoke(messages)

    print(f"📚 Info Agent: respuesta generada ({len(response.content)} chars)")

    # 5. Retornar — esto se mergea con el state
    return {
        "context": context,
        "response": response.content,
        "messages": [AIMessage(content=response.content)],
    }
