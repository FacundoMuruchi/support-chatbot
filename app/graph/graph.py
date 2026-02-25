"""
Ensamblado del StateGraph de LangGraph.

Este es el archivo central que conecta todos los nodos y define
el flujo del grafo.

Conceptos clave para aprender:
- StateGraph: grafo basado en estados (el estado viaja entre nodos).
- add_node: registra un nodo (función async) en el grafo.
- set_entry_point: define por dónde empieza la ejecución.
- add_edge: conexión directa A → B (siempre va).
- add_conditional_edges: conexión A → B o C según una condición.
- END: nodo especial que termina la ejecución.
- compile(): convierte el grafo en una app ejecutable.

Flujo visual:
    [START] → triage → (info? soporte?)
                ↓ info          ↓ soporte
           info_agent      support_agent
                ↓               ↓
            format_review ← ───┘
                ↓
              [END]
"""

from langgraph.graph import START, END, StateGraph

from app.graph.nodes.format_review import format_review_node
from app.graph.nodes.info_agent import info_agent_node
from app.graph.nodes.support_agent import support_agent_node
from app.graph.nodes.triage import route_by_intent, triage_node
from app.graph.state import SupportState


def build_graph() -> StateGraph:
    """
    Construye y compila el grafo multi-agente.

    Retorna la app compilada lista para invocar con:
        result = await app.ainvoke({"messages": [...], "user_phone": "..."})
    """

    # Crear el grafo con el schema de estado
    graph = StateGraph(SupportState)

    # Agregar nodos — cada uno es una función async
    graph.add_node("triage", triage_node)
    graph.add_node("info_agent", info_agent_node)
    graph.add_node("support_agent", support_agent_node)
    graph.add_node("format_review", format_review_node)

    graph.add_edge(START, "triage")
    graph.add_conditional_edges(
        "triage",           # Nodo de origen
        route_by_intent,    # Función que decide el destino
        {
            "info": "info_agent",        # Si intent == "info"
            "soporte": "support_agent",  # Si intent == "soporte"
        },
    )
    graph.add_edge("info_agent", "format_review")
    graph.add_edge("support_agent", "format_review")
    graph.add_edge("format_review", END)

    # Compilar y retornar
    app = graph.compile()
    print("✅ Grafo LangGraph compilado exitosamente")

    return app


# ── Instancia global del grafo ──────────────────────────────────
# Se importa desde otros módulos:
#   from app.graph.graph import support_app
support_app = build_graph()
