"""
Rutas del webhook de WhatsApp vía Kapso.

Endpoints:
- POST /webhook: Recibe eventos de Kapso (whatsapp.message.received)
- POST /test: Endpoint de prueba sin WhatsApp

Conceptos clave:
- Kapso envía webhooks con formato propio (message + conversation).
- BackgroundTasks permite responder 200 rápido mientras procesamos.
- thread_id (phone number) se pasa en config para que el checkpointer
  persista la conversación por usuario.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel

from langchain_core.messages import HumanMessage

from app.api.whatsapp import mark_as_read, parse_kapso_webhook, send_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
#  POST /webhook — Eventos de Kapso
# ═══════════════════════════════════════════════════════════════

async def process_message(support_app, phone: str, text: str, message_id: str):
    """
    Procesa un mensaje en background:
    1. Marca como leído (tildes azules + typing indicator)
    2. Invoca el grafo LangGraph con thread_id para memoria
    3. Envía la respuesta por WhatsApp
    """
    logger.info(f"📱 Mensaje de {phone}: {text}")

    try:
        # Marcar como leído (muestra "escribiendo..." al usuario)
        if message_id:
            await mark_as_read(message_id)

        # Invocar el grafo con memoria de conversación
        # El thread_id (phone) permite recordar mensajes anteriores
        result = await support_app.ainvoke(
            {
                "messages": [HumanMessage(content=text)],
                "user_phone": phone,
                "intent": "",
                "context": "",
                "response": "",
            },
            config={"configurable": {"thread_id": phone}},
        )

        # Obtener la respuesta formateada
        response = result.get("response", "")

        if not response:
            response = "😅 Disculpá, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?"

        # Enviar respuesta por WhatsApp
        await send_whatsapp_message(phone, response)

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}", exc_info=True)
        await send_whatsapp_message(
            phone,
            "😅 Hubo un error procesando tu mensaje. Por favor intentá de nuevo en unos minutos.",
        )


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Recibe eventos de webhook de Kapso.

    Kapso envía eventos como whatsapp.message.received cuando
    un usuario envía un mensaje al número de WhatsApp.

    El procesamiento ocurre en BackgroundTask para responder 200 rápido.
    """
    payload = await request.json()
    logger.info(f"📥 Webhook recibido: {payload}")

    # Obtener el grafo compilado desde app.state
    support_app = request.app.state.support_app

    # Parsear el mensaje entrante
    message_data = parse_kapso_webhook(payload)

    if message_data:
        logger.info(f"✅ Mensaje parseado: phone={message_data['phone']}, text={message_data['text'][:50]}...")
        background_tasks.add_task(
            process_message,
            support_app=support_app,
            phone=message_data["phone"],
            text=message_data["text"],
            message_id=message_data.get("message_id", ""),
        )
    else:
        logger.warning("⚠️ Webhook recibido pero no se pudo parsear como mensaje de texto")

    # Kapso espera 200 OK
    return Response(content="OK", status_code=200)


# ═══════════════════════════════════════════════════════════════
#  POST /test — Endpoint de prueba (sin WhatsApp)
# ═══════════════════════════════════════════════════════════════

class TestMessage(BaseModel):
    """Schema para el endpoint de test."""
    phone: str = "5491100000000"
    text: str


@router.post("/test")
async def test_endpoint(request: Request, msg: TestMessage):
    """
    Endpoint de prueba que simula un mensaje de WhatsApp.
    Ideal para testing sin necesidad de configurar Kapso.

    Ejemplo con curl:
        curl -X POST http://localhost:8000/test \\
            -H "Content-Type: application/json" \\
            -d '{"text": "¿Qué planes tienen?"}'
    """
    logger.info(f"🧪 TEST: Simulando mensaje de {msg.phone}: {msg.text}")

    # Obtener el grafo compilado desde app.state
    support_app = request.app.state.support_app

    try:
        result = await support_app.ainvoke(
            {
                "messages": [HumanMessage(content=msg.text)],
                "user_phone": msg.phone,
                "intent": "",
                "context": "",
                "response": "",
            },
            config={"configurable": {"thread_id": msg.phone}},
        )

        return {
            "intent": result.get("intent", ""),
            "response": result.get("response", ""),
            "context_preview": (
                result.get("context", "")[:200] + "..."
                if result.get("context")
                else ""
            ),
        }
    except Exception as e:
        logger.error(f"Error en test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
