from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
import base64
import os
import uuid

from app.dependencies import get_db
from app.models import Producto, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

class ProductoCreate(BaseModel):
    nombre: str
    precio: float
    descripcion: Optional[str] = None
    stock: Optional[int] = 0
    imagen_url: Optional[str] = None

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    precio: Optional[float] = None
    descripcion: Optional[str] = None
    stock: Optional[int] = None
    imagen_url: Optional[str] = None

router = APIRouter(prefix="/productos", tags=["Productos"])

def obtener_usuario_desde_token(token: str, db: Session) -> Optional[Usuario]:
    if not token:
        return None
    try:
        jwt_parts = token.split(".")
        if len(jwt_parts) == 3:
            payload_b64 = jwt_parts[1]
            padding = "=" * (4 - len(payload_b64) % 4)
            payload_json = base64.b64decode(payload_b64 + padding).decode("utf-8")
            data = json.loads(payload_json)
            sub = data.get("sub") or data.get("user_id") or data.get("id") or data.get("email")

            if sub:
                if str(sub).isdigit():
                    return db.query(Usuario).filter(Usuario.id == int(sub)).first()
                return db.query(Usuario).filter(Usuario.email == str(sub)).first()
    except Exception:
        pass
    return None

def verificar_admin(
    token_oauth: Optional[str] = Depends(oauth2_scheme),
    authorization_header: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
) -> Usuario:
    token = token_oauth
    if not token and authorization_header:
        parts = authorization_header.split(" ")
        token = parts[1] if len(parts) == 2 else parts[0]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere iniciar sesión para realizar esta acción."
        )

    usuario = obtener_usuario_desde_token(token, db)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o usuario no encontrado."
        )

    if getattr(usuario, "rol", "customer") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Solo los administradores pueden gestionar productos."
        )

    return usuario

# --- 1. LISTAR PRODUCTOS (Público) ---
@router.get("/", response_model=List[dict])
def listar_productos(db: Session = Depends(get_db)):
    productos = db.query(Producto).all()
    return [
        {
            "id": p.id,
            "nombre": getattr(p, "nombre", ""),
            "precio": getattr(p, "precio", 0.0),
            "descripcion": getattr(p, "descripcion", ""),
            "stock": getattr(p, "stock", 0),
            "imagen_url": getattr(p, "imagen_url", "")
        }
        for p in productos
    ]

# --- 2. OBTENER PRODUCTO POR ID (Público) ---
@router.get("/{producto_id}")
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="El producto no existe")
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "precio": producto.precio,
        "descripcion": producto.descripcion,
        "stock": getattr(producto, "stock", 0),
        "imagen_url": getattr(producto, "imagen_url", "")
    }

# --- 3. CREAR PRODUCTO (Solo Admin) ---
@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_producto(
    producto: ProductoCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    try:
        nuevo_producto = Producto(
            nombre=producto.nombre,
            precio=producto.precio,
            descripcion=producto.descripcion,
            stock=producto.stock or 0,
            imagen_url=producto.imagen_url
        )
        db.add(nuevo_producto)
        db.commit()
        db.refresh(nuevo_producto)
        return nuevo_producto
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el producto: {str(e)}")

# --- 4. ACTUALIZAR PRODUCTO (Solo Admin) ---
@router.put("/{producto_id}")
def actualizar_producto(
    producto_id: int,
    datos: ProductoUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="El producto no existe")

    if datos.nombre is not None:
        producto.nombre = datos.nombre
    if datos.precio is not None:
        producto.precio = datos.precio
    if datos.descripcion is not None:
        producto.descripcion = datos.descripcion
    if datos.stock is not None:
        producto.stock = datos.stock
    if datos.imagen_url is not None:
        producto.imagen_url = datos.imagen_url

    db.commit()
    db.refresh(producto)
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "precio": producto.precio,
        "descripcion": producto.descripcion,
        "stock": getattr(producto, "stock", 0),
        "imagen_url": getattr(producto, "imagen_url", "")
    }

# --- 5. SUBIR IMAGEN DE PRODUCTO (Solo Admin) ---
@router.post("/{producto_id}/imagen")
async def subir_imagen_producto(
    producto_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="El producto no existe")

    contenido = await archivo.read()
    if len(contenido) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="La imagen supera el límite de 2 MB.")

    es_png = contenido.startswith(b"\x89PNG\r\n\x1a\n")
    es_jpg = contenido.startswith(b"\xff\xd8\xff")
    es_webp = contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP"

    if not (es_png or es_jpg or es_webp):
        raise HTTPException(
            status_code=415,
            detail="Archivo inválido. Solo se permiten imágenes reales en formato PNG, JPG o WEBP."
        )

    ext = ".png" if es_png else (".jpg" if es_jpg else ".webp")
    os.makedirs("uploads", exist_ok=True)
    nombre_archivo = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join("uploads", nombre_archivo), "wb") as f:
        f.write(contenido)

    producto.imagen_url = f"/static/{nombre_archivo}"
    db.commit()
    db.refresh(producto)
    return {"imagen_url": producto.imagen_url}

# --- 6. ELIMINAR PRODUCTO (Solo Admin) ---
@router.delete("/{producto_id}", status_code=status.HTTP_200_OK)
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="El producto no existe")

    try:
        db.delete(producto)
        db.commit()
        return {"mensaje": f"Producto con ID {producto_id} eliminado con éxito"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar el producto: {str(e)}")