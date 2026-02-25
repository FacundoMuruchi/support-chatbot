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
                          │ Agente Info  │  │Agente Soporte│←──┐
                          │   (RAG)      │  │  (ToolNode)  │   │
                          └──────┬───────┘  └──────┬───────┘   │
                                 │          tools_condition    │
                                 │            ↓          ↓     │
                                 │         [tools] ──────┘   (no)
                                 └────────┬────────────────────┘
                                    ┌─────┴─────┐
                                    │  Formato   │  (WhatsApp-ready)
                                    └─────┬─────┘
                                   should_summarize?
                                    ↓            ↓
                              summarize        [END]
                                    ↓
                                  [END]
```

## 🚀 Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Orquestación | LangGraph (StateGraph) |
| LLM Principal | OpenRouter → Arcee AI Trinity Large Preview 400B |
| LLM Rápido | OpenRouter → NVIDIA Nemotron 3 Nano 30B (formato + resumen) |
| Vector DB | Pinecone Serverless |
| Embeddings | Pinecone Inference (`llama-text-embed-v2`, 1024 dims) |
| DB Relacional | PostgreSQL (Docker) |
| Memoria | LangGraph PostgresSaver (checkpointer por thread_id) |
| API | FastAPI + Uvicorn |
| WhatsApp | Kapso (proxy de WhatsApp Cloud API) |
| Observabilidad | LangSmith |

## 📋 Setup

### 1. Clonar y configurar entorno

```bash
git clone https://github.com/tu-usuario/fm-support.git
cd fm-support
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
copy .env.example .env
# Editar .env con tus API keys
```

### 3. Levantar PostgreSQL

```bash
docker compose up -d
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
curl -X POST http://localhost:8000/test ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"¿Qué planes tienen disponibles?\"}"
```

### 7. Conectar WhatsApp con Kapso

1. Crear cuenta en [Kapso](https://kapso.ai) y obtener API key
2. Configurar las variables `KAPSO_*` en `.env`
3. Exponer el servidor con `ngrok http 8000`
4. Configurar webhook en Kapso apuntando a `https://tu-url-ngrok/webhook`

## 📁 Estructura del Proyecto

```
support/
├── app/
│   ├── core/
│   │   ├── config.py              # Configuración centralizada
│   │   └── llm.py                 # Instancias LLM compartidas (llm, llm_strict, llm_format)
│   ├── db/
│   │   ├── database.py            # SQLAlchemy engine/session (TZ: Buenos Aires)
│   │   └── models.py              # Modelo Ticket (status, category enums)
│   ├── rag/vectorstore.py         # Pinecone Inference embeddings wrapper
│   ├── graph/
│   │   ├── state.py               # SupportState (messages, user_phone, intent, summary...)
│   │   ├── graph.py               # StateGraph + ToolNode + ReAct loop + summarize
│   │   └── nodes/
│   │       ├── triage.py          # Router LLM (info | soporte)
│   │       ├── info_agent.py      # Agente RAG (Pinecone + historial + summary)
│   │       ├── support_agent.py   # Agente con ToolNode (tickets DB)
│   │       ├── format_review.py   # Formateador para WhatsApp (modelo rápido)
│   │       └── summarize.py       # Resumen automático de conversación
│   └── api/
│       ├── main.py                # FastAPI app + lifespan + checkpointer
│       ├── whatsapp.py            # Parser Kapso + envío de mensajes
│       └── routes/webhook.py      # Endpoint /webhook
├── scripts/seed_pinecone.py       # Carga fm_data.txt → Pinecone
├── data/fm_data.txt               # Datos de FM.inc (planes, cobertura, FAQ)
├── docker-compose.yml             # PostgreSQL + Adminer
└── requirements.txt
```

## 🧠 Conceptos Clave

- **StateGraph**: Grafo basado en estados donde cada nodo lee y escribe un estado compartido.
- **MessagesState**: Los mensajes se *acumulan* automáticamente en vez de reemplazarse.
- **Conditional Edges**: El nodo de triaje decide dinámicamente qué agente invocar.
- **ToolNode + ReAct Loop**: El agente de soporte usa el patrón ReAct *en el grafo*: `support_agent → tools_condition → ToolNode → support_agent`.
- **Phone Injection**: El `user_phone` se inyecta en código antes de ejecutar tools — nunca se confía en el LLM para datos sensibles.
- **RAG**: El agente de información combina búsqueda semántica (Pinecone) con generación (LLM).
- **Pinecone Inference**: Embeddings generados server-side con `llama-text-embed-v2` (1024 dims).
- **Memoria**: `AsyncPostgresSaver` persiste conversaciones por `thread_id` (número de teléfono).
- **Resumen Automático**: Cuando el historial supera 6 mensajes conversacionales, se resumen los viejos y se mantienen los 2 más recientes.
- **LLM Compartido**: Tres instancias centralizadas en `llm.py` — `llm` (creativo), `llm_strict` (determinista), `llm_format` (rápido).

## 📄 Licencia

MIT
