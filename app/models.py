from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from app.db.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    imagen_url = Column(String, nullable=True)  # <-- OBLIGATORIO


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    rol = Column(String, default="customer", nullable=False)
    acepto_tratamiento = Column(Boolean, nullable=False)
    fecha_consentimiento = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    cantidad = Column(Integer, default=1)
    precio_unitario = Column(Float, nullable=True)
    total = Column(Float, nullable=False, default=0.0)
    fecha = Column(DateTime, default=datetime.utcnow)
    estado = Column(String, default="pendiente")