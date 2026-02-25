"""
Motor de base de datos SQLAlchemy y gestión de sesiones.

Usa SQLAlchemy síncrono con psycopg2 para simplicidad.
La conexión se establece al iniciar FastAPI y se cierra al apagar.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Motor de base de datos — timezone Buenos Aires en cada conexión
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"options": "-c timezone=America/Argentina/Buenos_Aires"},
)

# Factory de sesiones
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Session:
    """
    Genera una sesión de base de datos.
    Usar como dependency de FastAPI:
        session: Session = Depends(get_session)
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """
    Crea todas las tablas definidas en los modelos.
    Se ejecuta una vez al arrancar la aplicación.
    """
    from app.db.models import Base  # noqa: F811

    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada correctamente")
