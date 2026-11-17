"""Entorno aislado de pruebas: base de datos y carpetas temporales, sin IA externa ni scheduler.

Debe fijar las variables ANTES de importar `app` (la configuración se lee al importar).
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="gdoc_tests_")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_TMP}/test.db",
    "UPLOAD_DIR": os.path.join(_TMP, "storage"),
    "BATCH_DIR": os.path.join(_TMP, "batches"),
    "AUTOMATION_BACKOFF_SECONDS": "0",
    "SCHEDULER_ENABLED": "false",
    "GEMINI_API_KEY": "",
    "GROQ_API_KEY": "",
    "OLLAMA_BASE_URL": "",
    "AI_EXTERNAL_ALLOWED": "true",
    "VISION_REQUIRE_CONSENT": "true",
    "ADMIN_PASSWORD": "",
    "APP_ENV": "development",
    "SECRET_KEY": "clave-de-pruebas-0123456789abcdef0123456789abcdef",
})

import pytest  # noqa: E402

PASSWORD = "Password123*"


@pytest.fixture(scope="session", autouse=True)
def base_de_datos():
    import seed_data
    from app import auth, models
    from app.database import SessionLocal

    seed_data.init_db()
    db = SessionLocal()
    try:
        for agente in db.query(models.UsuarioAgente).all():
            agente.password_hash = auth.hash_password(PASSWORD)
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture()
def db():
    from app.database import SessionLocal
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _cliente_con_sesion(correo: str):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.post("/login", data={"email": correo, "password": PASSWORD}, follow_redirects=False)
    assert r.status_code == 303, r.text
    return c


@pytest.fixture()
def anonimo():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def agente():
    return _cliente_con_sesion("andres.gomez@empresa.com")


@pytest.fixture()
def otro_agente():
    return _cliente_con_sesion("laura.gomez@empresa.com")


@pytest.fixture()
def admin():
    return _cliente_con_sesion("miguel.rojas@empresa.com")


@pytest.fixture()
def png_bytes():
    """Imagen PNG válida y mínima (la extracción real la simulan los mocks)."""
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(buf, format="PNG")
    return buf.getvalue()
