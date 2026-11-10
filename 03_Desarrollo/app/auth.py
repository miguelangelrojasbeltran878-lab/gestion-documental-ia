"""Módulo de seguridad, hashing de contraseñas y gestión de sesiones mediante tokens firmados (itsdangerous)."""
import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, config

serializer = URLSafeTimedSerializer(config.SECRET_KEY)
COOKIE_NAME = "session_token"
MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 días


def hash_password(password: str) -> str:
    """Genera hash PBKDF2-SHA256 con salt aleatorio."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña plana coincide con el hash PBKDF2."""
    if not hashed_password or not hashed_password.startswith("pbkdf2:sha256:"):
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        salt = parts[1]
        stored_hash = parts[2]
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return secrets.compare_digest(stored_hash, key.hex())
    except Exception:
        return False


def create_session_token(data: Dict[str, Any]) -> str:
    """Crea token de sesión firmado criptográficamente."""
    return serializer.dumps(data)


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica y valida firma y caducidad del token de sesión."""
    try:
        return serializer.loads(token, max_age=MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[models.UsuarioAgente]:
    """Obtiene el usuario autenticado a partir de la cookie de sesión o header Authorization."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    data = decode_session_token(token)
    if not data or "id_agente" not in data:
        return None

    user = db.query(models.UsuarioAgente).filter(models.UsuarioAgente.id_agente == data["id_agente"]).first()
    if user and user.activo:
        return user
    return None


def require_authenticated_agent(user: Optional[models.UsuarioAgente] = Depends(get_current_user)) -> models.UsuarioAgente:
    """Dependencia para rutas protegidas que requieren un agente autenticado."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere iniciar sesión para acceder a este recurso.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_admin(user: models.UsuarioAgente = Depends(require_authenticated_agent)) -> models.UsuarioAgente:
    """Dependencia para rutas que requieren rol Administrador."""
    if user.rol != "Administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: requiere privilegios de Administrador."
        )
    return user
