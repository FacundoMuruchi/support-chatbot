"""
Aplicación FastAPI principal.

Punto de entrada del servidor. Configura:
- Lifespan (inicialización de DB y checkpointer al arrancar)
- CORS middleware
- Logging
- Rutas del webhook

Para ejecutar:
    uvicorn app.api.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.api.routes.webhook import router as webhook_router
from app.core.config import settings
from app.db.database import init_db
from app.graph.graph import build_graph

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
    - Crea el checkpointer (PostgresSaver) para memoria de conversación
    - Compila el grafo con el checkpointer

    Shutdown:
    - Cierra el pool de conexiones del checkpointer
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

    # Inicializar DB (tablas de tickets)
    init_db()

    # Inicializar checkpointer (tablas de memoria)
    connection_string = settings.database_url

    # Setup necesita autocommit (CREATE INDEX CONCURRENTLY no corre en transaction)
    import psycopg
    setup_conn = await psycopg.AsyncConnection.connect(connection_string, autocommit=True)
    setup_checkpointer = AsyncPostgresSaver(setup_conn)
    await setup_checkpointer.setup()
    await setup_conn.close()

    # Pool para el checkpointer de runtime
    pool = AsyncConnectionPool(
        conninfo=connection_string,
        max_size=5,
        open=False,
    )
    await pool.open()

    checkpointer = AsyncPostgresSaver(pool)
    logger.info("🧠 Checkpointer PostgreSQL inicializado (memoria de conversación activa)")

    # Compilar grafo con checkpointer y hacerlo accesible desde las rutas
    app.state.support_app = build_graph(checkpointer=checkpointer)

    logger.info("✅ Sistema listo para recibir mensajes")

    yield  # La app corre aquí

    # ── Shutdown ──
    logger.info("👋 Apagando FM.inc Support System...")
    await pool.close()


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

# ── Rutas ────────────────────────────────────────────────────────
app.include_router(webhook_router)


@app.get("/")
async def health_check():
    """Health check y documentación de endpoints."""
    return {
        "service": "FM.inc Support System",
        "status": "running",
        "version": "1.0.0",
        "memory": "PostgresSaver (conversation persistence)",
        "whatsapp_provider": "Kapso",
        "endpoints": {
            "webhook": "POST /webhook",
            "test": "POST /test",
            "docs": "GET /docs",
            "health": "GET /",
        },
    }
