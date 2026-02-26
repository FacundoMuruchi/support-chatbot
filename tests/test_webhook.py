"""
Tests para el parsing del webhook de Kapso.

Estos tests no requieren conexión a servicios externos — solo
verifican que parse_kapso_webhook() extraiga correctamente los
datos de los payloads de Kapso.
"""

from app.api.whatsapp import parse_kapso_webhook


# ── Fixtures: payloads reales de Kapso ──

VALID_TEXT_PAYLOAD = {
    "message": {
        "from": "541125037150",
        "id": "wamid.ABC123",
        "type": "text",
        "text": {"body": "hola, necesito ayuda"},
    },
    "conversation": {
        "id": "conv-123",
        "contact_name": "Facu",
    },
}

IMAGE_PAYLOAD = {
    "message": {
        "from": "541125037150",
        "type": "image",
        "image": {"caption": "foto"},
    },
}

EMPTY_PAYLOAD = {}


# ── Tests ──

def test_parse_valid_text_message():
    """Parsea correctamente un mensaje de texto."""
    result = parse_kapso_webhook(VALID_TEXT_PAYLOAD)

    assert result is not None
    assert result["phone"] == "541125037150"
    assert result["text"] == "hola, necesito ayuda"
    assert result["message_id"] == "wamid.ABC123"


def test_parse_ignores_image_message():
    """Ignora mensajes que no son de texto (imagen, audio, etc.)."""
    result = parse_kapso_webhook(IMAGE_PAYLOAD)
    assert result is None


def test_parse_empty_payload():
    """Devuelve None si el payload está vacío."""
    result = parse_kapso_webhook(EMPTY_PAYLOAD)
    assert result is None


def test_parse_missing_text_body():
    """Maneja payload con type=text pero sin body."""
    payload = {
        "message": {
            "from": "5491100000000",
            "type": "text",
            "text": {},
        }
    }
    result = parse_kapso_webhook(payload)
    assert result is not None
    assert result["text"] == ""
