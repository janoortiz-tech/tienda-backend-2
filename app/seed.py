import os
from app.db.database import SessionLocal
from app.models import Usuario, Producto
from app.core.security import get_password_hash

def run_seed():
    db = SessionLocal()
    try:
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@equipo.com")
        admin_pass = os.getenv("SEED_ADMIN_PASSWORD", "AdminClave123!")

        admin = db.query(Usuario).filter(Usuario.email == admin_email).first()
        if not admin:
            db.add(Usuario(
                nombre="Administrador",
                email=admin_email,
                hashed_password=get_password_hash(admin_pass),
                rol="admin",
                acepto_tratamiento=True,
            ))

        productos_demo = [
            {
                "nombre": "iPhone 13",
                "descripcion": "128 GB - Excelente rendimiento",
                "precio": 499.0,
                "stock": 10,
                "imagen_url": "/demo/iphone13.jpg",
            },
        ]

        for item in productos_demo:
            existe = db.query(Producto).filter(Producto.nombre == item["nombre"]).first()
            if not existe:
                db.add(Producto(**item))

        db.commit()
        print("Seed listo.")
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()