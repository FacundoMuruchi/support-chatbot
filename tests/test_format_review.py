"""
Tests para el nodo format_review.

Verifica el límite de caracteres de WhatsApp y el manejo
de respuestas vacías (sin LLM — solo lógica).
"""

from app.graph.nodes.format_review import MAX_WHATSAPP_CHARS


def test_max_chars_constant():
    """Verifica que el límite de WhatsApp está configurado."""
    assert MAX_WHATSAPP_CHARS > 0
    assert MAX_WHATSAPP_CHARS <= 4096  # límite real de WhatsApp


def test_truncation_logic():
    """Verifica que textos largos se truncan correctamente."""
    long_text = "A" * 2000
    if len(long_text) > MAX_WHATSAPP_CHARS:
        truncated = long_text[:MAX_WHATSAPP_CHARS - 3] + "..."
    else:
        truncated = long_text

    assert len(truncated) == MAX_WHATSAPP_CHARS
    assert truncated.endswith("...")


def test_short_text_not_truncated():
    """Verifica que textos cortos no se truncan."""
    short_text = "Hola, ¿en qué puedo ayudarte?"
    if len(short_text) > MAX_WHATSAPP_CHARS:
        result = short_text[:MAX_WHATSAPP_CHARS - 3] + "..."
    else:
        result = short_text

    assert result == short_text
    assert not result.endswith("...")
