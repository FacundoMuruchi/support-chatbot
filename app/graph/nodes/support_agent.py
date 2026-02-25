"""
Agente de Soporte Técnico (Tool-Based).

Interactúa con PostgreSQL para gestionar tickets de averías.

Conceptos clave para aprender:
- Tool Calling: el LLM decide QUÉ herramienta usar y CON QUÉ parámetros.
- Definimos tools como funciones Python con @tool.
- El LLM genera un tool_call, nosotros lo ejecutamos, y le devolvemos
  el resultado para que genere la respuesta final.
- Este patrón es el corazón de los "agentes" en LangGraph.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Ticket, TicketCategory, TicketStatus
from app.graph.state import SupportState

# ── LLM con tool calling ────────────────────────────────────────
llm = ChatOpenAI(
    model=settings.openrouter_model,
    openai_api_key=settings.openrouter_api_key,
    openai_api_base=settings.openrouter_base_url,
    temperature=0,
)

# ── Prompt del agente de soporte ─────────────────────────────────
SUPPORT_SYSTEM_PROMPT = """Eres el agente de soporte técnico de FM.inc, una empresa de telefonía móvil.

Tu rol es ayudar a los usuarios con problemas técnicos usando las herramientas disponibles.

HERRAMIENTAS DISPONIBLES:
1. create_ticket: Crea un nuevo ticket de soporte. Categorías válidas: señal, internet, facturacion, equipo, otro
2. get_ticket_status: Consulta el estado de un ticket por su ID
3. list_user_tickets: Lista todos los tickets de un usuario

REGLAS:
1. Si el usuario reporta un problema, usa create_ticket con una descripción clara.
2. Si pregunta por un ticket específico (ej: "ticket #5"), usa get_ticket_status.
3. Si quiere ver sus tickets, usa list_user_tickets.
4. Siempre confirma la acción realizada al usuario.
5. Sé empático con los problemas del usuario.
6. Clasifica la categoría del problema correctamente.
"""


# ═══════════════════════════════════════════════════════════════
#  TOOLS — Funciones que el LLM puede invocar
# ═══════════════════════════════════════════════════════════════

@tool
def create_ticket(phone_number: str, description: str, category: str) -> str:
    """
    Crea un nuevo ticket de soporte técnico en la base de datos.

    Args:
        phone_number: Número de WhatsApp del usuario (ej: "5491112345678")
        description: Descripción del problema reportado
        category: Categoría del problema. Debe ser una de: señal, internet, facturacion, equipo, otro
    """
    # Validar categoría
    try:
        cat = TicketCategory(category)
    except ValueError:
        cat = TicketCategory.OTRO

    session = SessionLocal()
    try:
        ticket = Ticket(
            phone_number=phone_number,
            description=description,
            category=cat,
            status=TicketStatus.ABIERTO,
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)

        return (
            f"✅ Ticket #{ticket.id} creado exitosamente.\n"
            f"Categoría: {ticket.category.value}\n"
            f"Estado: {ticket.status.value}\n"
            f"Descripción: {ticket.description}"
        )
    finally:
        session.close()


@tool
def get_ticket_status(ticket_id: int) -> str:
    """
    Consulta el estado de un ticket de soporte por su ID.

    Args:
        ticket_id: Número de ticket (ej: 1, 2, 3...)
    """
    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()

        if not ticket:
            return f"❌ No se encontró ningún ticket con ID #{ticket_id}."

        return (
            f"📋 Ticket #{ticket.id}\n"
            f"Estado: {ticket.status.value}\n"
            f"Categoría: {ticket.category.value}\n"
            f"Descripción: {ticket.description}\n"
            f"Creado: {ticket.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
    finally:
        session.close()


@tool
def list_user_tickets(phone_number: str) -> str:
    """
    Lista todos los tickets de soporte de un usuario.

    Args:
        phone_number: Número de WhatsApp del usuario (ej: "5491112345678")
    """
    session = SessionLocal()
    try:
        tickets = (
            session.query(Ticket)
            .filter(Ticket.phone_number == phone_number)
            .order_by(Ticket.created_at.desc())
            .limit(10)
            .all()
        )

        if not tickets:
            return "📭 No tenés tickets de soporte registrados."

        lines = [f"📋 Tus tickets de soporte ({len(tickets)}):\n"]
        for t in tickets:
            emoji = {"abierto": "🟡", "en_progreso": "🔵", "resuelto": "🟢"}.get(
                t.status.value, "⚪"
            )
            lines.append(
                f"{emoji} #{t.id} — {t.category.value} — {t.status.value}\n"
                f"   {t.description[:60]}..."
            )

        return "\n".join(lines)
    finally:
        session.close()


# Lista de tools para bind al LLM
tools = [create_ticket, get_ticket_status, list_user_tickets]

# LLM con tools bindeados — esto le dice al LLM qué tools puede usar
llm_with_tools = llm.bind_tools(tools)

# Dict para ejecutar tools por nombre
tool_map = {t.name: t for t in tools}


async def support_agent_node(state: SupportState) -> dict:
    """
    Nodo de soporte: usa tool calling para interactuar con la DB.

    Flujo (ReAct pattern simplificado):
    1. Envía el mensaje del usuario al LLM con tools disponibles
    2. Si el LLM genera un tool_call → ejecuta la tool
    3. Devuelve el resultado de la tool al LLM
    4. El LLM genera la respuesta final para el usuario

    Conceptos clave:
    - El LLM NO ejecuta las tools directamente, solo genera
      la INTENCIÓN de llamarlas (tool_call).
    - Nosotros ejecutamos la tool y le devolvemos el resultado
      en un ToolMessage.
    - El LLM usa ese resultado para formular la respuesta.
    """
    last_message = state["messages"][-1]
    user_phone = state.get("user_phone", "desconocido")

    # 1. Primera llamada al LLM (puede generar tool_calls)
    messages = [
        SystemMessage(content=SUPPORT_SYSTEM_PROMPT),
        HumanMessage(
            content=f"[Número del usuario: {user_phone}]\n\n{last_message.content}"
        ),
    ]

    ai_response = await llm_with_tools.ainvoke(messages)
    messages.append(ai_response)

    # DEBUG: ver qué devuelve el LLM
    print(f"🔧 Support Agent DEBUG: tool_calls={ai_response.tool_calls}, content_len={len(ai_response.content)}")

    # 2. Si hay tool_calls, ejecutarlas
    if ai_response.tool_calls:
        print(f"🔧 Support Agent: {len(ai_response.tool_calls)} tool calls detectados")

        for tool_call in ai_response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"   → Ejecutando {tool_name}({tool_args})")

            # Ejecutar la tool
            selected_tool = tool_map[tool_name]
            tool_result = selected_tool.invoke(tool_args)

            # Agregar resultado como ToolMessage
            messages.append(ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"],
            ))

        # 3. Segunda llamada al LLM con los resultados de las tools
        final_response = await llm_with_tools.ainvoke(messages)
        response_text = final_response.content
    else:
        # El LLM respondió directamente sin usar tools
        response_text = ai_response.content

    # Fallback si la respuesta está vacía
    if not response_text.strip():
        print("⚠️ Support Agent: respuesta vacía, usando fallback")
        response_text = "Disculpá, no pude procesar tu solicitud. Por favor intentá de nuevo o contactá al 0800-555-FMINC."

    print(f"🔧 Support Agent: respuesta generada ({len(response_text)} chars)")

    return {
        "response": response_text,
        "messages": [AIMessage(content=response_text)],
    }
