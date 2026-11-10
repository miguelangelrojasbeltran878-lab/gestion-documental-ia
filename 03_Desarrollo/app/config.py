"""Configuración centralizada. Todos los valores sensibles se leen de variables de entorno (.env)."""
import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:  # python-dotenv es opcional
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP_ENV = os.getenv("APP_ENV", "development")
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)  # en producción debe definirse
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'tickets.db')}")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "storage"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# IA (Gemini nivel gratuito). Si no hay clave, el sistema usa el Plan B (reglas locales).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))
# Autorización explícita para enviar datos a un proveedor externo (Ley 1581). Si es "false" solo se usa procesamiento local.
AI_EXTERNAL_ALLOWED = os.getenv("AI_EXTERNAL_ALLOWED", "true").lower() == "true"

# Visión
VISION_MAX_MB = int(os.getenv("VISION_MAX_MB", "10"))
VISION_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_CONFIDENCE_THRESHOLD", "0.75"))

# Automatización
AUTOMATION_MAX_ATTEMPTS = int(os.getenv("AUTOMATION_MAX_ATTEMPTS", "3"))

# Usuario administrador inicial (solo se crea si no existe ningún usuario)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@portal.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

os.makedirs(UPLOAD_DIR, exist_ok=True)
