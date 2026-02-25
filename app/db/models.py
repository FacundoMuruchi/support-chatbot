"""
Modelos SQLAlchemy para el sistema de tickets de soporte.

Tabla principal: Ticket
- Almacena reportes de averías y consultas de soporte técnico.
- Cada ticket está asociado al número de WhatsApp del usuario.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos."""
    pass


class TicketStatus(str, enum.Enum):
    """Estados posibles de un ticket de soporte."""
    ABIERTO = "abierto"
    EN_PROGRESO = "en_progreso"
    RESUELTO = "resuelto"


class TicketCategory(str, enum.Enum):
    """Categorías de problemas reportados."""
    SEÑAL = "señal"
    INTERNET = "internet"
    FACTURACION = "facturacion"
    EQUIPO = "equipo"
    OTRO = "otro"


class Ticket(Base):
    """
    Modelo de ticket de soporte técnico.

    Ejemplo de uso:
        ticket = Ticket(
            phone_number="5491112345678",
            description="No tengo señal en zona norte",
            category=TicketCategory.SEÑAL,
        )
    """

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.ABIERTO, nullable=False
    )
    category: Mapped[TicketCategory] = mapped_column(
        Enum(TicketCategory), default=TicketCategory.OTRO, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Ticket #{self.id} [{self.status.value}] {self.category.value}>"
