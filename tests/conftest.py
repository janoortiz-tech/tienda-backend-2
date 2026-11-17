import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base
from app.dependencies import get_db
from app import models
from tests.ayudantes import registrar, token_de

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SesionPrueba = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_prueba():
    with SesionPrueba() as db:
        yield db


@pytest.fixture
def client():
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_db] = get_db_prueba
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture
def cliente(client):
    return token_de(client, *registrar(client))


@pytest.fixture
def admin(client):
    email, password = registrar(client, email="admin@prueba.com")
    with SesionPrueba() as db:
        usuario = db.query(models.Usuario).filter_by(email=email).one()
        usuario.rol = "admin"
        db.commit()
    return token_de(client, email, password)


@pytest.fixture
def producto(client, admin):
    r = client.post(
        "/productos",
        headers=admin,
        json={
            "nombre": "iPhone de prueba",
            "descripcion": "Para los tests",
            "precio": 1000,
        },
    )
    assert r.status_code == 201, r.text
    datos = r.json()
    with SesionPrueba() as db:
        prod = db.query(models.Producto).filter_by(id=datos["id"]).one()
        prod.stock = 2
        db.commit()
    datos["stock"] = 2
    return datos