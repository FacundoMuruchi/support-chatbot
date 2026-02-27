"""
Ensamblado del StateGraph de LangGraph.
"""

import logging

from langgraph.graph import START, END, StateGraph

logger = logging.getLogger(__name__)
from langgraph.prebuilt import tools_condition, ToolNode

from app.graph.nodes.format_review import format_review_node
from app.graph.nodes.info_agent import info_agent_node
from app.graph.nodes.summarize import should_summarize, summarize_conversation
from app.graph.nodes.support_agent import support_agent_node, tools
from app.graph.nodes.triage import route_by_intent, triage_node
from app.graph.state import SupportState

def _route_support(state: SupportState) -> str:
    """
    Después de support_agent:
    - Si hay tool_calls → "support_tools"
    - Si no → "format_review"
    """
    result = tools_condition(state)
    if result == "tools":
        return "support_tools"
    return "format_review"


def build_graph(checkpointer=None):
    """
    Construye y compila el grafo multi-agente.
    """
    graph = StateGraph(SupportState)

    # Nodos
    graph.add_node("triage", triage_node)
    graph.add_node("info_agent", info_agent_node)
    graph.add_node("support_agent", support_agent_node)
    graph.add_node("support_tools", ToolNode(tools))
    graph.add_node("format_review", format_review_node)
    graph.add_node("summarize_conversation", summarize_conversation)

    # Edges
    graph.add_edge(START, "triage")
    graph.add_conditional_edges("triage", route_by_intent, {"info": "info_agent", "soporte": "support_agent"})
    graph.add_edge("info_agent", "format_review")

    # ReAct loop: support_agent → (tools? → support_agent) | format_review
    graph.add_conditional_edges("support_agent", _route_support)
    graph.add_edge("support_tools", "support_agent")

    # Después de format_review: ¿hay que resumir?
    graph.add_conditional_edges("format_review", should_summarize)
    graph.add_edge("summarize_conversation", END)

    app = graph.compile(checkpointer=checkpointer)
    logger.info("✅ Grafo LangGraph compilado exitosamente")

    return app
