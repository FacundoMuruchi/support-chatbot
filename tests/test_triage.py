"""
Tests para el nodo de triaje y la función de routing.

Verifica que route_by_intent devuelve el intent correcto
del state (sin LLM — solo lógica de routing).
"""

from app.graph.nodes.triage import route_by_intent


def test_route_info_intent():
    """Verifica que intent='info' rutea correctamente."""
    state = {"intent": "info", "messages": []}
    assert route_by_intent(state) == "info"


def test_route_soporte_intent():
    """Verifica que intent='soporte' rutea correctamente."""
    state = {"intent": "soporte", "messages": []}
    assert route_by_intent(state) == "soporte"
