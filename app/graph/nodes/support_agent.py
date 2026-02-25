"""
Agente de Soporte Técnico (Tool-Based).

Interactúa con PostgreSQL para gestionar tickets de averías.

Conceptos clave:
- Tool Calling: el LLM decide QUÉ herramienta usar y CON QUÉ parámetros.
- Definimos tools como funciones Python con @tool.
- El grafo usa ToolNode para ejecutar las tools automáticamente.
- El loop ReAct (LLM → tool → LLM) está en el grafo, no acá.
"""

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool

from app.core.llm import llm_strict as llm
from app.db.database import SessionLocal
from app.db.models import Ticket, TicketCategory, TicketStatus
from app.graph.state import SupportState

# ── Prompt del agente de soporte ─────────────────────────────────
SUPPORT_SYSTEM_PROMPT = """Eres el agente de soporte técnico de FM.inc, una empresa de telefonía móvil.

FLUJO OBLIGATORIO PARA CREAR TICKETS:
1. El usuario dice que tiene un problema → VOS PREGUNTÁS: "¿Podrías contarme más sobre el problema?"
2. El usuario describe el problema con detalle → RECIÉN AHÍ usás create_ticket
3. NUNCA llames a create_ticket si el usuario solo dijo "quiero reportar un problema" o similar sin dar detalles.

Ejemplo CORRECTO:
- Usuario: "quiero reportar un averío"
- Vos: "¡Claro! ¿Podrías contarme qué problema estás teniendo? Por ejemplo: ¿es de señal, internet, facturación?"
- Usuario: "no tengo internet hace 2 días"
- Vos: [create_ticket con descripción "Sin servicio de internet desde hace 2 días"]

Ejemplo INCORRECTO (NUNCA hagas esto):
- Usuario: "quiero reportar un averío"
- Vos: [create_ticket] ← ERROR: no sabés cuál es el problema todavía

HERRAMIENTAS:
1. create_ticket: Crea ticket. Categorías: señal, internet, facturacion, equipo, otro
2. get_ticket_status: Estado de un ticket por ID
3. list_user_tickets: Lista tickets del usuario

OTRAS REGLAS:
- Usá el número de "[Número del usuario: ...]" para las tools. NUNCA pidas el número.
- Sé empático y profesional.
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


# ── Exports para graph.py ────────────────────────────────────────
tools = [create_ticket, get_ticket_status, list_user_tickets]
llm_with_tools = llm.bind_tools(tools)


async def support_agent_node(state: SupportState) -> dict:
    """
    Nodo del agente: solo llama al LLM con tools.
    Si el LLM genera tool_calls, el grafo los enruta a support_tools.
    Si no, la respuesta va directo a format_review.
    """
    user_phone = state.get("user_phone", "desconocido")

    summary = state.get("summary", "")
    messages = [
        SystemMessage(content=SUPPORT_SYSTEM_PROMPT),
        SystemMessage(content=f"[Número del usuario: {user_phone}]"),
    ]
    if summary:
        messages.append(SystemMessage(content=f"Resumen de la conversación anterior: {summary}"))
    messages.extend(state["messages"])

    response = await llm_with_tools.ainvoke(messages)

    return {"messages": [response]}
