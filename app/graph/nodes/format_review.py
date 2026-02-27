"""
Nodo de Revisión de Formato.

Último nodo del grafo. Toma la respuesta raw de los agentes y la
adapta para el formato de WhatsApp usando lógica Python pura — sin LLM.

Transformaciones que aplica:
- Elimina markdown no soportado por WhatsApp (##, ```, _italic_)
- Convierte **negrita** al formato de WhatsApp (*negrita*)
- Convierte listas markdown (- item) a bullets con emoji (• item)
- Trunca a MAX_WHATSAPP_CHARS si el mensaje es demasiado largo
"""

import logging
import re

from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

from app.graph.state import SupportState

MAX_WHATSAPP_CHARS = 1500


def _format_for_whatsapp(text: str) -> str:
    # 1. Eliminar bloques de código (``` ... ```)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()

    # 2. Eliminar encabezados markdown (## Título → Título)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # 3. Convertir **negrita** → *negrita* (formato WhatsApp)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # 4. Eliminar _cursiva_ markdown (WhatsApp usa _ también, pero evitar dobles)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)

    # 5. Convertir listas markdown (- item o * item) a bullets con •
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)

    # 6. Colapsar más de dos saltos de línea consecutivos
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 7. Truncar si supera el límite de WhatsApp
    if len(text) > MAX_WHATSAPP_CHARS:
        text = text[:MAX_WHATSAPP_CHARS - 3] + "..."

    return text.strip()


async def format_review_node(state: SupportState) -> dict:
    """
    Nodo de formato: adapta la respuesta para WhatsApp sin usar LLM.

    Busca la respuesta en state["response"].
    """
    raw_response = state["response"]
    formatted = _format_for_whatsapp(raw_response) if raw_response else "😅 Disculpá, no pude procesar tu mensaje. ¿Podrías intentar de nuevo?"
    logger.info(f"📝 Format Review: {len(raw_response)} → {len(formatted)} chars")
    return {
        "response": formatted
    }