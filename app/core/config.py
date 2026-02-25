"""
Configuración centralizada del proyecto.

Carga TODAS las variables desde .env usando python-dotenv.
El archivo .env es la ÚNICA fuente de verdad para la configuración.

Este módulo simplemente expone las variables como un objeto tipado
para tener autocompletado en el IDE.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto Y exportar al OS
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=True)


class Settings:
    """Lee configuración de las variables de entorno (cargadas desde .env)."""

    # ── OpenRouter ──
    @property
    def openrouter_api_key(self) -> str:
        return os.environ.get("OPENROUTER_API_KEY", "")
    
    @property
    def openrouter_base_url(self) -> str:
        return os.environ.get("OPENROUTER_BASE_URL", "")

    # ── Pinecone ──
    @property
    def pinecone_api_key(self) -> str:
        return os.environ.get("PINECONE_API_KEY", "")

    @property
    def pinecone_index_name(self) -> str:
        return os.environ.get("PINECONE_INDEX_NAME", "")

    @property
    def pinecone_embedding_model(self) -> str:
        return os.environ.get("PINECONE_EMBEDDING_MODEL", "")

    # ── PostgreSQL ──
    @property
    def database_url(self) -> str:
        return os.environ.get("DATABASE_URL", "")

    # ── Kapso (WhatsApp) ──
    @property
    def kapso_api_base_url(self) -> str:
        return os.environ.get("KAPSO_API_BASE_URL", "")

    @property
    def kapso_api_key(self) -> str:
        return os.environ.get("KAPSO_API_KEY", "")

    @property
    def whatsapp_phone_number_id(self) -> str:
        return os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")

    @property
    def meta_graph_version(self) -> str:
        return os.environ.get("META_GRAPH_VERSION", "")

    @property
    def kapso_whatsapp_url(self) -> str:
        """URL base para la API de WhatsApp vía proxy de Kapso."""
        return f"{self.kapso_api_base_url}/meta/whatsapp/{self.meta_graph_version}"

    # ── LangSmith ──
    @property
    def langsmith_tracing(self) -> str:
        return os.environ.get("LANGSMITH_TRACING", "")

    @property
    def langsmith_api_key(self) -> str:
        return os.environ.get("LANGSMITH_API_KEY", "")

    @property
    def langsmith_project(self) -> str:
        return os.environ.get("LANGSMITH_PROJECT", "")


# Singleton — importar desde cualquier módulo
settings = Settings()
