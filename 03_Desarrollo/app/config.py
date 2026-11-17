"""Configuración centralizada. Todos los valores sensibles se leen de variables de entorno (.env)."""
import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:  # python-dotenv es opcional
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "si", "sí")


APP_ENV = os.getenv("APP_ENV", "development")


def _clave_secreta() -> str:
    """SECRET_KEY del entorno; si falta, se genera una vez y se guarda en .secret_key (ignorado por git)
    para que reiniciar el servidor no cierre las sesiones. En producción debe definirse por entorno."""
    if os.getenv("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    ruta = os.path.join(BASE_DIR, ".secret_key")
    try:
        with open(ruta, encoding="utf-8") as fh:
            valor = fh.read().strip()
            if len(valor) >= 32:
                return valor
    except OSError:
        pass
    valor = secrets.token_hex(32)
    try:
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write(valor)
    except OSError:
        pass
    return valor


SECRET_KEY = _clave_secreta()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'tickets.db')}")
# Render/Heroku entregan "postgres://", SQLAlchemy exige "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "storage"))
BATCH_DIR = os.getenv("BATCH_DIR", os.path.join(BASE_DIR, "temp_batches"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
COOKIE_SECURE = _bool("COOKIE_SECURE", "true" if APP_ENV == "production" else "false")
# Secreto para firmar URLs de descarga de archivos de lote (HMAC). Nunca incrustado en el código.
FILE_TOKEN_SECRET = os.getenv("FILE_TOKEN_SECRET") or SECRET_KEY

# ---------------------------------------------------------------------------
# IA: cadena de proveedores gratuitos con Plan B (Gemini -> Groq -> Ollama local -> reglas)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "").rstrip("/")  # vacío = Ollama desactivado
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")
# Orden de preferencia. Los proveedores sin credenciales se omiten automáticamente.
AI_PROVIDER_ORDER = [p.strip().lower() for p in os.getenv("AI_PROVIDER_ORDER", "gemini,groq,ollama").split(",") if p.strip()]
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))
# Autorización para enviar datos a proveedores externos (Ley 1581). Si es false solo se usa Ollama local / reglas.
AI_EXTERNAL_ALLOWED = _bool("AI_EXTERNAL_ALLOWED", "true")

# ---------------------------------------------------------------------------
# Visión por computador
# ---------------------------------------------------------------------------
VISION_MAX_MB = int(os.getenv("VISION_MAX_MB", "15"))
VISION_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_CONFIDENCE_THRESHOLD", "0.75"))
# Si es true, la imagen solo viaja a un servicio externo cuando quien la sube marca la autorización expresa.
VISION_REQUIRE_CONSENT = _bool("VISION_REQUIRE_CONSENT", "true")
# Idiomas de Tesseract (requiere el binario tesseract instalado; si no existe se omite el OCR local).
OCR_LANGS = os.getenv("OCR_LANGS", "spa+eng")

# ---------------------------------------------------------------------------
# Automatización (motor propio)
# ---------------------------------------------------------------------------
AUTOMATION_MAX_ATTEMPTS = int(os.getenv("AUTOMATION_MAX_ATTEMPTS", "3"))
AUTOMATION_BACKOFF_SECONDS = float(os.getenv("AUTOMATION_BACKOFF_SECONDS", "1"))
SCHEDULER_ENABLED = _bool("SCHEDULER_ENABLED", "true")
SLA_ALERT_MINUTES = int(os.getenv("SLA_ALERT_MINUTES", "120"))
RETRY_QUEUE_MINUTES = int(os.getenv("RETRY_QUEUE_MINUTES", "10"))
SLA_CHECK_MINUTES = int(os.getenv("SLA_CHECK_MINUTES", "15"))

# Usuario administrador inicial (solo se crea si no existe ningún usuario)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@portal.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(BATCH_DIR, exist_ok=True)
