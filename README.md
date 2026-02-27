# 📱 FM.inc — Multi-Agent Support System

Sistema multi-agente de soporte técnico para una empresa de telefonía móvil, construido con **LangGraph**, **Pinecone**, **PostgreSQL**, **FastAPI** y **WhatsApp vía Kapso**.

## 🏗️ Arquitectura

```mermaid
graph TD
    WA["📱 WhatsApp"] --> K["Kapso"]
    K -->|POST /webhook| API["FastAPI"]
    API -->|BackgroundTask| G["LangGraph StateGraph"]

    G --> T["🔀 Triage"]
    T -->|"intent: info"| IA["📚 Info Agent<br/>(RAG + Pinecone)"]
    T -->|"intent: soporte"| SA["🔧 Support Agent"]

    SA -->|tool_calls?| TC{"tools_condition"}
    TC -->|sí| TOOLS["⚙️ ToolNode<br/>(inject phone)"]
    TOOLS -->|resultado| SA
    TC -->|no| FR["📝 Format Review"]

    IA --> FR
    FR -->|respuesta| SUM{"should_summarize?"}
    SUM -->|">6 msgs"| SC["🧠 Summarize"]
    SUM -->|"≤6 msgs"| REPLY["📱 WhatsApp Reply"]
    SC --> REPLY

    style T fill:#f59e0b,color:#000
    style IA fill:#3b82f6,color:#fff
    style SA fill:#8b5cf6,color:#fff
    style TOOLS fill:#6366f1,color:#fff
    style FR fill:#10b981,color:#fff
    style SC fill:#ec4899,color:#fff
```

## 🚀 Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Orquestación | LangGraph (StateGraph) |
| LLM | OpenRouter → OpenAI GPT-OSS:120B |
| Vector DB | Pinecone Serverless |
| Embeddings | Pinecone Inference (`llama-text-embed-v2`, 1024 dims) |
| DB Relacional | PostgreSQL (Docker) |
| Memoria | LangGraph PostgresSaver (checkpointer por thread_id) |
| API | FastAPI + Uvicorn |
| WhatsApp | Kapso (proxy de WhatsApp Cloud API) |
| Observabilidad | LangSmith |
| Desarrollo asistido | Google Antigravity |

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
│   │   └── llm.py                 # LLM compartido + retry con backoff
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
├── tests/
│   ├── test_webhook.py            # Parsing de payloads Kapso
│   ├── test_tools.py              # CRUD de tickets (SQLite en memoria)
│   ├── test_format_review.py      # Límite de caracteres WhatsApp
│   └── test_triage.py             # Routing de intents
├── scripts/seed_pinecone.py       # Carga fm_data.txt → Pinecone
├── data/fm_data.txt               # Datos de FM.inc (planes, cobertura, FAQ)
├── docker-compose.yml             # PostgreSQL + Adminer
├── pytest.ini                     # Configuración de pytest
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
- **Retry con Backoff**: `invoke_with_retry` maneja rate limits (429) con backoff exponencial (3 intentos).

## 🧪 Tests

```bash
pytest tests/ -v
```

15 tests que verifican:
- Parsing de webhooks Kapso (text, imagen, vacío)
- CRUD de tickets con SQLite en memoria
- Enums de estado y categoría
- Límite de caracteres de WhatsApp
- Routing de intents