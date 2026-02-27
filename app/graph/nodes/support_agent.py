"""
Agente de Soporte Técnico (Tool-Based).

Interactúa con PostgreSQL para gestionar tickets de averías.

Conceptos clave:
- Tool Calling: el LLM decide QUÉ herramienta usar y CON QUÉ parámetros.
- Definimos tools como funciones Python con @tool.
- El grafo usa ToolNode para ejecutar las tools automáticamente.
- El loop ReAct (LLM → tool → LLM) está en el grafo, no acá.
"""

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

from app.core.llm import invoke_with_retry, llm, tono_negocio
from app.db.database import SessionLocal
from app.db.models import Ticket, TicketCategory, TicketStatus
from app.graph.state import SupportState

# ── Prompt del agente de soporte ─────────────────────────────────
SUPPORT_SYSTEM_PROMPT = f"""Eres el agente de soporte técnico de FM.inc, una empresa de telefonía móvil.

REGLAS ESTRICTAS PARA TICKETS:
1. NUNCA crees un ticket en el primer mensaje, incluso si parece tener cierta información.
2. Si el usuario dice que tiene un problema o quiere reportar una avería, PRIMERO PREGUNTALE los detalles (qué pasa exactamente, desde cuándo). Sólo después de que responda con la descripción del problema, usás `create_ticket` pasandole la descripción del problema y la categoría.
3. Si YA CREASTE un ticket en esta misma conversación y el usuario te da más información, DEBES usar `update_ticket`. NO crees uno nuevo bajo ninguna circunstancia.

EJEMPLO CORRECTO:
Usuario: "quiero reportar un averío"
Tú: "¡Claro! ¿Podrías contarme qué problema estás teniendo? Por ejemplo: ¿es de señal, internet, facturación?"
Usuario: "no tengo señal hace 2 días"
Tú: [Usás create_ticket] "¡Listo, acabo de abrir el ticket para que lo revisen! ✅ ¿Este problema te ocurre en una zona en particular o en todos lados?"
Usuario: "solo en el centro"
Tú: [Usás update_ticket agregando la zona] "Perfecto, ya sumé ese dato al reporte. ¿Te puedo ayudar con algo más?"

4. Nunca pidas el número de teléfono, ya lo tenés.

HERRAMIENTAS:
1. create_ticket: Crea ticket inicial. Categorías: señal, internet, facturacion, equipo, otro
2. update_ticket: Agrega detalles extras a un ticket que YA fue creado.
3. get_ticket_status: Estado de un ticket por ID
4. list_user_tickets: Lista tickets del usuario

FORMATO DE RESPUESTA:
{tono_negocio}
"""


# ═══════════════════════════════════════════════════════════════
#  TOOLS — Funciones que el LLM puede invocar
# ═══════════════════════════════════════════════════════════════

@tool
def create_ticket(user_phone: Annotated[str, InjectedState("user_phone")], description: str, category: str) -> str:
    """
    Crea un nuevo ticket de soporte técnico en la base de datos.

    Args:
        user_phone: Número de WhatsApp del usuario (ej: "5491112345678")
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
            phone_number=user_phone,
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
    except Exception as e:
        session.rollback()
        return f"❌ Error creando ticket: {e}"
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
def list_user_tickets(user_phone: Annotated[str, InjectedState("user_phone")]) -> str:
    """
    Lista todos los tickets de soporte de un usuario.

    Args:
        user_phone: Número de WhatsApp del usuario (ej: "5491112345678")
    """
    session = SessionLocal()
    try:
        tickets = (
            session.query(Ticket)
            .filter(Ticket.phone_number == user_phone)
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


@tool
def update_ticket(ticket_id: int, add_notes: str) -> str:
    """
    Agrega notas o detalles adicionales a un ticket existente.
    Usá esta herramienta IMPERATIVAMENTE si el usuario da más contexto 
    sobre un problema por el que YA abriste un ticket recientemente.

    Args:
        ticket_id: Número de ticket a actualizar
        add_notes: Nuevos detalles a agregar a la descripción existente
    """
    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()

        if not ticket:
            return f"❌ No se encontró ningún ticket con ID #{ticket_id}."

        ticket.description = f"{ticket.description}\n[UPDATE]: {add_notes}"
        session.commit()

        return f"✅ Ticket #{ticket_id} actualizado con la nueva información."
    except Exception as e:
        session.rollback()
        return f"❌ Error actualizando ticket: {e}"
    finally:
        session.close()


# ── Exports para graph.py ────────────────────────────────────────
tools = [create_ticket, get_ticket_status, list_user_tickets, update_ticket]
llm_with_tools = llm.bind_tools(tools)


async def support_agent_node(state: SupportState) -> dict:
    """
    Nodo del agente: solo llama al LLM con tools.
    Si el LLM genera tool_calls, el grafo los enruta a support_tools.
    Si no, la respuesta va directo a format_review.
    """
    summary = state.get("summary", "")
    messages = [
        SystemMessage(content=SUPPORT_SYSTEM_PROMPT)
    ]
    if summary:
        messages.append(SystemMessage(content=f"Resumen de la conversación anterior: {summary}"))
    messages.extend(state["messages"])

    response = await invoke_with_retry(llm_with_tools, messages)

    return {
        "response": response.content,
        "messages": [response]
    }
