from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = (
    {"check_same_thread": False}
    if db_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,   # Prueba la conexión antes de usarla (Clase 12)
    pool_recycle=300,     # Renueva conexiones cada 5 minutos (Clase 12)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()