# 📱 FM.inc — Multi-Agent Support System

Sistema multi-agente de soporte técnico para una empresa de telefonía móvil, construido con **LangGraph**, **Pinecone**, **PostgreSQL**, **FastAPI** y **WhatsApp vía Kapso**.

## 🏗️ Arquitectura

```
WhatsApp → Kapso Webhook → FastAPI → LangGraph StateGraph
                                          │
                                    ┌─────┴─────┐
                                    │   Triaje   │  (Router LLM)
                                    └─────┬─────┘
                                 ┌────────┴────────┐
                            info │                 │ soporte
                                 ▼                 ▼
                          ┌──────────────┐  ┌──────────────┐
                          │ Agente Info  │  │Agente Soporte│
                          │   (RAG)      │  │  (SQL Tools) │
                          └──────┬───────┘  └──────┬───────┘
                                 └────────┬────────┘
                                    ┌─────┴─────┐
                                    │  Formato   │  (WhatsApp-ready)
                                    └─────┬─────┘
                                          ▼
                                 Kapso → WhatsApp Reply
```

## 🚀 Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Orquestación | LangGraph (StateGraph) |
| LLM | OpenRouter (`openai/gpt-oss-120b:free`) |
| Vector DB | Pinecone Serverless |
| Embeddings | HuggingFace (`all-MiniLM-L6-v2`) |
| DB Relacional | PostgreSQL 16 (Docker) |
| API | FastAPI + Uvicorn |
| WhatsApp | Kapso (proxy de WhatsApp Cloud API) |
| Observabilidad | LangSmith |

## 📋 Setup

### 1. Clonar y configurar entorno

```bash
cd support
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
copy .env.example .env
# Editar .env con tus API keys (OpenRouter, Pinecone, Kapso, LangSmith)
```

### 3. Levantar PostgreSQL

```bash
docker-compose up -d
```

### 4. Cargar datos en Pinecone

```bash
python scripts/seed_pinecone.py
```

### 5. Iniciar el servidor

```bash
uvicorn app.api.main:app --reload --port 8000
```

### 6. Probar (sin WhatsApp)

```bash
# Info sobre planes
curl -X POST http://localhost:8000/test ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"¿Qué planes tienen disponibles?\"}"

# Reportar avería
curl -X POST http://localhost:8000/test ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"No tengo señal en zona norte, quiero reportar el problema\"}"
```

### 7. Conectar WhatsApp con Kapso

1. Crear cuenta en [Kapso](https://kapso.ai) y obtener API key
2. Configurar `KAPSO_API_BASE_URL` y `KAPSO_API_KEY` en `.env`
3. Configurar webhook en Kapso apuntando a `https://tu-servidor/webhook`
4. Suscribirse al evento `whatsapp.message.received`

## 📁 Estructura del Proyecto

```
support/
├── app/
│   ├── core/config.py              # Configuración centralizada
│   ├── db/
│   │   ├── database.py             # SQLAlchemy engine/session
│   │   └── models.py               # Modelo Ticket
│   ├── rag/vectorstore.py          # Pinecone + embeddings
│   ├── graph/
│   │   ├── state.py                # Estado compartido (TypedDict)
│   │   ├── graph.py                # Ensamblado del StateGraph
│   │   └── nodes/
│   │       ├── triage.py           # Router LLM
│   │       ├── info_agent.py       # Agente RAG
│   │       ├── support_agent.py    # Agente SQL Tools
│   │       └── format_review.py    # Formateador WhatsApp
│   └── api/
│       ├── main.py                 # FastAPI app
│       ├── whatsapp.py             # Helpers Kapso/WhatsApp
│       └── routes/webhook.py       # Endpoints
├── scripts/seed_pinecone.py        # Seed de datos
├── data/fm_data.json               # Datos ficticios FM.inc
├── docker-compose.yml
└── requirements.txt
```

## 🧠 Conceptos Clave

- **StateGraph**: Grafo basado en estados donde cada nodo lee y escribe un estado compartido.
- **add_messages reducer**: Los mensajes se *acumulan* en vez de reemplazarse.
- **Conditional Edges**: El nodo de triaje decide dinámicamente qué agente invocar.
- **Tool Calling**: El agente de soporte usa el LLM para decidir qué herramienta SQL invocar.
- **RAG**: El agente de información combina búsqueda semántica (Pinecone) con generación (LLM).
- **Kapso Proxy**: WhatsApp Cloud API con auth simplificada (`X-API-Key`), historial de mensajes y webhooks estructurados.
