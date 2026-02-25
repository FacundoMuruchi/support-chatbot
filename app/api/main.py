"""
Aplicación FastAPI principal.

Punto de entrada del servidor. Configura:
- Lifespan (inicialización de DB al arrancar)
- CORS middleware
- Logging
- Rutas del webhook

Para ejecutar:
    uvicorn app.api.main:app --reload --port 8000

Referencia: .agents/skills/fastapi-templates/SKILL.md
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.webhook import router as webhook_router
from app.core.config import settings
from app.db.database import init_db

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan handler: se ejecuta al arrancar y apagar el servidor.

    Startup:
    - Inicializa la base de datos (crea tablas si no existen)
    - Valida configuración crítica

    Shutdown:
    - Limpieza de recursos
    """
    # ── Startup ──
    logger.info("🚀 Iniciando FM.inc Support System...")

    # Validar configuración
    if not settings.openrouter_api_key:
        logger.warning("⚠️  OPENROUTER_API_KEY no configurada — el LLM no funcionará")
    if not settings.kapso_api_key:
        logger.warning("⚠️  KAPSO_API_KEY no configurada — WhatsApp no funcionará")
    if not settings.pinecone_api_key:
        logger.warning("⚠️  PINECONE_API_KEY no configurada — RAG no funcionará")

    init_db()
    logger.info("✅ Sistema listo para recibir mensajes")

    yield  # La app corre aquí

    # ── Shutdown ──
    logger.info("👋 Apagando FM.inc Support System...")


# ── App FastAPI ──────────────────────────────────────────────────
app = FastAPI(
    title="FM.inc Support System",
    description=(
        "Sistema multi-agente de soporte técnico para FM.inc. "
        "Integra LangGraph, Pinecone (RAG), PostgreSQL y WhatsApp vía Kapso."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rutas ────────────────────────────────────────────────────────
app.include_router(webhook_router)


@app.get("/")
async def health_check():
    """Health check y documentación de endpoints."""
    return {
        "service": "FM.inc Support System",
        "status": "running",
        "version": "1.0.0",
        "whatsapp_provider": "Kapso",
        "endpoints": {
            "webhook": "POST /webhook",
            "test": "POST /test",
            "docs": "GET /docs",
            "health": "GET /",
        },
    }
