import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import engine, Base
from app.dependencies import get_db
import app.models as models
from app.routers import auth, productos, pedidos

app = FastAPI()

# Crear todas las tablas automáticamente si no existen
Base.metadata.create_all(bind=engine)

# Compresión GZip para respuestas mayores a 1 KB (Clase 12)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS dinámico: lee CORS_ORIGINS en Render o usa localhost por defecto (Clase 11)
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [o.strip().rstrip("/") for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Caché de 30 días para imágenes estáticas y de demo (Clase 12)
class StaticConCache(StaticFiles):
    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        if respuesta.status_code == 200:
            respuesta.headers["Cache-Control"] = "public, max-age=2592000, immutable"
        return respuesta

# Asegurar que existan las carpetas antes de montarlas (Clase 11)
Path("uploads/productos").mkdir(parents=True, exist_ok=True)
Path("app/static/demo").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticConCache(directory="uploads"), name="static")
app.mount("/demo", StaticConCache(directory="app/static/demo"), name="demo")

# Endpoint de salud y verificación de base de datos (Clases 11 y 13)
@app.get("/salud", tags=["Salud"])
def salud(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"estado": "ok", "base": "ok"}

# Registrar routers de la API
app.include_router(auth.router)
app.include_router(productos.router)
app.include_router(pedidos.router)
app.include_router(pedidos.router_arrepentimiento)