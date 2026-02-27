"""
Carga fm_data.txt en Pinecone.

Uso:
    python scripts/seed_pinecone.py

Lee data/fm_data.txt, lo divide en chunks por secciones (---),
genera embeddings con Pinecone Inference y los sube al índice.
"""

import sys
from pathlib import Path

# Agregar el root del proyecto al path para que encuentre 'app'
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore

from app.core.config import settings
from app.rag.vectorstore import embeddings

# ── Leer archivo ──
data_path = Path(__file__).parent.parent / "data" / "fm_data.txt"
raw_text = data_path.read_text(encoding="utf-8")

# ── Dividir en chunks por sección ──
sections = raw_text.split("\n# ")

docs = []
for section in sections:
    content = section.strip()

    # Ignorar secciones vacías
    if not content:
        continue

    # Restaurar el "# " que se perdió al hacer el split
    content = "# " + content

    doc = Document(
        page_content=content,
        metadata={"source": "fm_data.txt"}
    )
    docs.append(doc)

print(f"📄 Archivo: {data_path.name}")
print(f"✂️  Chunks generados: {len(docs)}")

# ── Subir a Pinecone ──
vectorstore = PineconeVectorStore.from_documents(
    documents=docs,
    embedding=embeddings,
    index_name=settings.pinecone_index_name,
    pinecone_api_key=settings.pinecone_api_key,
)

print(f"✅ {len(docs)} chunks subidos a Pinecone ({settings.pinecone_index_name})")
