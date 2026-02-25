"""
Vector Store con Pinecone Inference.

Usa el modelo integrado de Pinecone `llama-text-embed-v2` para generar
embeddings del lado del servidor. Esto significa:
- NO necesitás instalar modelos de embeddings localmente
- NO necesitás sentence-transformers ni torch
- Pinecone genera los embeddings con el modelo NVIDIA llama-text-embed-v2
- Dimensión: 1024

Para que LangChain pueda usar los embeddings de Pinecone Inference,
creamos un wrapper `PineconeInferenceEmbeddings` que implementa
la interfaz de LangChain.
"""

from typing import List

from langchain_core.embeddings import Embeddings
from pinecone import Pinecone

from app.core.config import settings


class PineconeInferenceEmbeddings(Embeddings):
    """
    Wrapper de LangChain para Pinecone Inference API.

    Permite usar el modelo `llama-text-embed-v2` de Pinecone
    como fuente de embeddings dentro del ecosistema LangChain.

    input_type:
    - "passage" → para indexar documentos (al hacer upsert)
    - "query"  → para búsquedas (al hacer query)
    """

    def __init__(self):
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.model = settings.pinecone_embedding_model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Genera embeddings para una lista de documentos (input_type=passage)."""
        response = self.pc.inference.embed(
            model=self.model,
            inputs=[{"text": t} for t in texts],
            parameters={"input_type": "passage", "truncate": "END"},
        )
        return [item["values"] for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        """Genera embedding para una query de búsqueda (input_type=query)."""
        response = self.pc.inference.embed(
            model=self.model,
            inputs=[{"text": text}],
            parameters={"input_type": "query", "truncate": "END"},
        )
        return response.data[0]["values"]


# ── Instancias reutilizables ──
embeddings = PineconeInferenceEmbeddings()


def get_retriever(k: int = 4):
    """
    Crea un retriever de LangChain conectado a Pinecone.

    Usa los embeddings de Pinecone Inference (llama-text-embed-v2)
    para buscar documentos relevantes.
    """
    from langchain_pinecone import PineconeVectorStore

    vectorstore = PineconeVectorStore(
        index_name=settings.pinecone_index_name,
        embedding=embeddings,
        pinecone_api_key=settings.pinecone_api_key,
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})
