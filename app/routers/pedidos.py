from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import json
import base64
import uuid

from app.dependencies import get_db
from app.models import Pedido, Usuario, Producto

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

class PedidoCreate(BaseModel):
    producto_id: int
    cantidad: Optional[int] = 1

class CambiarEstadoPedido(BaseModel):
    estado: str

class ArrepentimientoCreate(BaseModel):
    pedido_id: int
    email: str

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])
router_arrepentimiento = APIRouter(tags=["Arrepentimiento"])

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

def obtener_usuario_actual(
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
            detail="Se requiere iniciar sesión para esta acción."
        )

    usuario = obtener_usuario_desde_token(token, db)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado."
        )
    return usuario

def verificar_admin(
    usuario: Usuario = Depends(obtener_usuario_actual)
) -> Usuario:
    if getattr(usuario, "rol", "customer") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Solo los administradores pueden realizar esta acción."
        )
    return usuario

# --- 1. CREAR PEDIDO ---
@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_pedido(
    pedido: PedidoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    producto = db.query(Producto).filter(Producto.id == pedido.producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail=f"No existe el producto con ID #{pedido.producto_id}")

    cantidad = pedido.cantidad or 1
    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero.")

    stock_actual = getattr(producto, "stock", 0) or 0
    if stock_actual < cantidad:
        raise HTTPException(status_code=409, detail="Stock insuficiente para completar la compra.")

    try:
        producto.stock = stock_actual - cantidad
        nuevo_pedido = Pedido(
            usuario_id=usuario.id,
            producto_id=producto.id,
            cantidad=cantidad,
            precio_unitario=float(producto.precio),
            total=float(producto.precio * cantidad),
            estado="pendiente"
        )
        db.add(nuevo_pedido)
        db.commit()
        db.refresh(nuevo_pedido)

        return {
            "id": nuevo_pedido.id,
            "usuario_id": usuario.id,
            "producto_id": producto.id,
            "producto_nombre": producto.nombre,
            "cantidad": nuevo_pedido.cantidad,
            "precio_unitario": nuevo_pedido.precio_unitario,
            "total": nuevo_pedido.total,
            "estado": nuevo_pedido.estado
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el pedido: {str(e)}")

# --- 2. LISTAR MIS PEDIDOS (Soporta /pedidos/mios y /pedidos/) ---
@router.get("/mios")
@router.get("/")
def listar_mis_pedidos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    try:
        pedidos = db.query(Pedido).filter(Pedido.usuario_id == usuario.id).order_by(Pedido.id.asc()).all()
        resultado = []
        for p in pedidos:
            prod_nombre = "Producto no encontrado"
            if getattr(p, "producto_id", None):
                prod = db.query(Producto).filter(Producto.id == p.producto_id).first()
                if prod:
                    prod_nombre = prod.nombre

            resultado.append({
                "id": p.id,
                "producto_id": getattr(p, "producto_id", None),
                "producto_nombre": prod_nombre,
                "cantidad": getattr(p, "cantidad", 1) or 1,
                "precio_unitario": getattr(p, "precio_unitario", None),
                "total": getattr(p, "total", 0.0),
                "estado": getattr(p, "estado", "pendiente") or "pendiente"
            })
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener lista de pedidos: {str(e)}")

# --- 3. LISTAR TODOS LOS PEDIDOS (Solo Admin) ---
@router.get("/todos")
def listar_todos_los_pedidos(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    try:
        pedidos = db.query(Pedido).order_by(Pedido.id.desc()).all()
        resultado = []
        for p in pedidos:
            user_email = "Usuario desconocido"
            if getattr(p, "usuario_id", None):
                user = db.query(Usuario).filter(Usuario.id == p.usuario_id).first()
                if user:
                    user_email = user.email

            prod_nombre = "Producto no encontrado"
            if getattr(p, "producto_id", None):
                prod = db.query(Producto).filter(Producto.id == p.producto_id).first()
                if prod:
                    prod_nombre = prod.nombre

            resultado.append({
                "id": p.id,
                "usuario_id": getattr(p, "usuario_id", None),
                "usuario_email": user_email,
                "producto_id": getattr(p, "producto_id", None),
                "producto_nombre": prod_nombre,
                "cantidad": getattr(p, "cantidad", 1) or 1,
                "precio_unitario": getattr(p, "precio_unitario", None),
                "total": getattr(p, "total", 0.0),
                "estado": getattr(p, "estado", "pendiente") or "pendiente"
            })
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar todos los pedidos: {str(e)}")

# --- 4. BUSCAR UN PEDIDO INDIVIDUAL POR ID ---
@router.get("/{pedido_id}")
def obtener_pedido_por_id(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail=f"No existe el pedido con el ID #{pedido_id}")

    if pedido.usuario_id != usuario.id and getattr(usuario, "rol", "customer") != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos para ver este pedido.")

    prod_nombre = "Producto no encontrado"
    if getattr(pedido, "producto_id", None):
        prod = db.query(Producto).filter(Producto.id == pedido.producto_id).first()
        if prod:
            prod_nombre = prod.nombre

    return {
        "id": pedido.id,
        "usuario_id": getattr(pedido, "usuario_id", None),
        "producto_id": getattr(pedido, "producto_id", None),
        "producto_nombre": prod_nombre,
        "cantidad": getattr(pedido, "cantidad", 1) or 1,
        "precio_unitario": getattr(pedido, "precio_unitario", None),
        "total": getattr(pedido, "total", 0.0),
        "estado": getattr(pedido, "estado", "pendiente") or "pendiente"
    }

# --- 5. CAMBIAR ESTADO DEL PEDIDO (Solo Admin) ---
@router.put("/{pedido_id}/estado")
def cambiar_estado_pedido(
    pedido_id: int,
    datos: CambiarEstadoPedido,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    estados_validos = ["pendiente", "completado", "reembolsado", "aprobado", "cancelado"]
    estado_norm = datos.estado.lower().strip()

    if estado_norm not in estados_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Opciones permitidas: {', '.join(estados_validos)}"
        )

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="El pedido no existe.")

    pedido.estado = estado_norm
    db.commit()
    db.refresh(pedido)

    return {
        "mensaje": f"Pedido #{pedido_id} actualizado a '{estado_norm}'",
        "pedido_id": pedido_id,
        "nuevo_estado": pedido.estado
    }

# --- 6. ELIMINAR PEDIDO (Solo Admin) ---
@router.delete("/{pedido_id}")
def eliminar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_admin)
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="El pedido no existe.")

    try:
        db.delete(pedido)
        db.commit()
        return {"mensaje": f"Pedido #{pedido_id} eliminado con éxito"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar pedido: {str(e)}")

# --- 7. BOTÓN DE ARREPENTIMIENTO (Público, respuesta uniforme) ---
@router_arrepentimiento.post("/arrepentimiento", status_code=status.HTTP_201_CREATED)
def solicitar_arrepentimiento(
    datos: ArrepentimientoCreate,
    db: Session = Depends(get_db)
):
    pedido = db.query(Pedido).filter(Pedido.id == datos.pedido_id).first()
    if pedido and getattr(pedido, "estado", "") != "cancelado":
        dueno = db.query(Usuario).filter(Usuario.id == pedido.usuario_id).first()
        if dueno and dueno.email.lower().strip() == datos.email.lower().strip():
            pedido.estado = "cancelado"
            if getattr(pedido, "producto_id", None):
                prod = db.query(Producto).filter(Producto.id == pedido.producto_id).first()
                if prod:
                    prod.stock = (getattr(prod, "stock", 0) or 0) + (getattr(pedido, "cantidad", 1) or 1)
            db.commit()

    return {
        "codigo": f"ARR-{uuid.uuid4().hex[:8].upper()}",
        "mensaje": "Solicitud recibida. Si los datos corresponden a una compra válida, se procesará la cancelación."
    }