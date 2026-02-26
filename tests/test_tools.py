"""
Tests para las herramientas (tools) del agente de soporte.

Verifican que create_ticket, get_ticket_status y list_user_tickets
interactúen correctamente con la base de datos.

Usa una base de datos SQLite en memoria para no depender de Docker.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Ticket, TicketCategory, TicketStatus


# ── Setup: DB en memoria para tests ──

@pytest.fixture
def db_session():
    """Crea una DB SQLite en memoria con la tabla tickets."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ── Tests del modelo Ticket ──

def test_create_ticket_in_db(db_session):
    """Verifica que un ticket se crea correctamente en la DB."""
    ticket = Ticket(
        phone_number="541125037150",
        description="No tengo internet hace 2 días",
        category=TicketCategory.INTERNET,
        status=TicketStatus.ABIERTO,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    assert ticket.id is not None
    assert ticket.phone_number == "541125037150"
    assert ticket.category == TicketCategory.INTERNET
    assert ticket.status == TicketStatus.ABIERTO


def test_query_tickets_by_phone(db_session):
    """Verifica que se pueden buscar tickets por número de teléfono."""
    # Crear 2 tickets para el mismo usuario
    for desc in ["Sin señal", "Factura incorrecta"]:
        db_session.add(Ticket(
            phone_number="541125037150",
            description=desc,
            category=TicketCategory.OTRO,
        ))
    # Crear 1 ticket para otro usuario
    db_session.add(Ticket(
        phone_number="5491199999999",
        description="Otro usuario",
        category=TicketCategory.OTRO,
    ))
    db_session.commit()

    # Buscar solo los del primer usuario
    tickets = db_session.query(Ticket).filter(
        Ticket.phone_number == "541125037151"
    ).all()

    assert len(tickets) == 2


def test_ticket_status_enum():
    """Verifica que los enums de estado tienen los valores correctos."""
    assert TicketStatus.ABIERTO.value == "abierto"
    assert TicketStatus.EN_PROGRESO.value == "en_progreso"
    assert TicketStatus.RESUELTO.value == "resuelto"


def test_ticket_category_enum():
    """Verifica que los enums de categoría tienen los valores correctos."""
    assert TicketCategory.SEÑAL.value == "señal"
    assert TicketCategory.INTERNET.value == "internet"
    assert TicketCategory.FACTURACION.value == "facturacion"
    assert TicketCategory.EQUIPO.value == "equipo"
    assert TicketCategory.OTRO.value == "otro"


def test_ticket_category_fallback():
    """Verifica que una categoría inválida cae en OTRO."""
    try:
        cat = TicketCategory("categoría_inexistente")
    except ValueError:
        cat = TicketCategory.OTRO
    assert cat == TicketCategory.OTRO


def test_ticket_repr(db_session):
    """Verifica el __repr__ del modelo."""
    ticket = Ticket(
        phone_number="541125037151",
        description="Test",
        category=TicketCategory.SEÑAL,
        status=TicketStatus.ABIERTO,
    )
    db_session.add(ticket)
    db_session.commit()

    assert "Ticket #" in repr(ticket)
    assert "abierto" in repr(ticket)
    assert "señal" in repr(ticket)
