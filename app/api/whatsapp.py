"""
Helpers para interactuar con WhatsApp vía Kapso Proxy.

Kapso actúa como proxy de la WhatsApp Cloud API de Meta, añadiendo:
- Autenticación simplificada (X-API-Key en vez de Bearer token)
- Almacenamiento de mensajes y conversaciones
- Webhooks con payload estructurado

Referencia: .agents/skills/integrate-whatsapp/references/whatsapp-api-reference.md

Conceptos clave:
- Base URL: {KAPSO_API_BASE_URL}/meta/whatsapp/{META_GRAPH_VERSION}
- Auth: Header X-API-Key (no Bearer token)
- Los payloads son idénticos a la Meta Cloud API
- Kapso agrega features extra (query history, buffering, etc.)
"""

from typing import Optional

import httpx

from app.core.config import settings


def parse_kapso_webhook(payload: dict) -> Optional[dict]:
    """
    Extrae el mensaje de texto del payload de un webhook de Kapso.

    Kapso envía el payload con la estructura:
    { "message": { "from": "...", "text": {"body": "..."}, "type": "text" },
      "conversation": {...}, "phone_number_id": "..." }

    Returns:
        dict con {"phone": str, "text": str, "message_id": str} o None.
    """
    message = payload.get("message", {})

    if message.get("type") != "text":
        return None

    return {
        "phone": message.get("from", ""),
        "text": message.get("text", {}).get("body", ""),
        "message_id": message.get("id", ""),
    }


async def send_whatsapp_message(phone: str, message: str) -> bool:
    """
    Envía un mensaje de texto por WhatsApp vía Kapso proxy.

    Usa el endpoint:
        POST {KAPSO_API_BASE_URL}/meta/whatsapp/{version}/{phone_number_id}/messages

    El payload es idéntico al de la Meta Cloud API.

    Args:
        phone: Número del destinatario (formato internacional sin +)
        message: Texto del mensaje

    Returns:
        True si se envió correctamente.
    """
    url = f"{settings.kapso_whatsapp_url}/{settings.whatsapp_phone_number_id}/messages"

    headers = {
        "X-API-Key": settings.kapso_api_key,
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code == 200:
                print(f"📤 Mensaje enviado a {phone} ({len(message)} chars)")
                return True
            else:
                print(f"❌ Error enviando mensaje: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error de conexión con Kapso API: {e}")
            return False


async def mark_as_read(message_id: str) -> bool:
    """
    Marca un mensaje como leído en WhatsApp.

    Esto muestra las tildes azules al usuario y opcionalmente
    un indicador de escritura.

    Ref: whatsapp-api-reference.md → Mark as read
    """
    url = f"{settings.kapso_whatsapp_url}/{settings.whatsapp_phone_number_id}/messages"

    headers = {
        "X-API-Key": settings.kapso_api_key,
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {"type": "text"},  # Muestra "escribiendo..."
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers)
            return response.status_code == 200
        except Exception:
            return False
