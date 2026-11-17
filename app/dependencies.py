from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

# Importamos SessionLocal para definir get_db aquí mismo
from app.db.database import SessionLocal
from app.models import Usuario

# Importa settings si tienes tu configuración centralizada (o ajusta según tu proyecto)
try:
    # pyrefly: ignore [missing-import]
    from app.config import settings
except ImportError:
    pass

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Generador de sesiones de Base de Datos para los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        tipo_token: str = payload.get("tipo")

        if email is None or tipo_token != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None:
        raise credentials_exception

    return usuario


def require_admin(usuario_actual: Usuario = Depends(get_current_user)):
    return usuario_actual