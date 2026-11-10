import pytest
import os
import io
from fastapi.testclient import TestClient
from app.main import app
from app import auth, vision_service, automation_engine, config

client = TestClient(app)

def test_homepage_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "EduSupport AI" in response.text
    assert "Visión Multimodal" in response.text

def test_login_invalid_credentials():
    response = client.post("/login", data={"email": "noexiste@empresa.com", "password": "wrong"})
    assert response.status_code == 401
    assert "Credenciales inválidas" in response.text

def test_login_valid_credentials():
    response = client.post("/login", data={"email": "andres.gomez@empresa.com", "password": "Password123*"}, follow_redirects=False)
    assert response.status_code == 303
    assert auth.COOKIE_NAME in response.cookies

def test_password_hashing():
    pwd = "MiContraseñaSegura123!"
    hashed = auth.hash_password(pwd)
    assert auth.verify_password(pwd, hashed) is True
    assert auth.verify_password("incorrecta", hashed) is False

def test_vision_module_page():
    response = client.get("/vision")
    assert response.status_code == 200
    assert "Módulo de Visión por Computador" in response.text

def test_vision_api_processing_and_confidence():
    fake_img = b"Factura Electronica FE-999. Emisor: Tech SAS. NIT: 900.123.456-1. Total: $500,000 COP."
    files = {"archivo": ("factura_test.png", fake_img, "image/png")}
    data = {"cargado_por": "test_unitario"}
    response = client.post("/api/v1/vision/procesar", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["ok"] is True
    assert "codigo" in res
    assert res["tipo_documento"] == "factura"
    assert "confianza" in res

def test_automation_engine_audit_log():
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    count = db.query(models.EjecucionAutomatizacion).count()
    assert count >= 1
    db.close()

def test_real_dashboard_metrics():
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    metrics = response.json()
    assert "total_tickets" in metrics
    assert "total_ejecuciones_automatizacion" in metrics
    assert "tasa_exito_automatizacion" in metrics
    assert "total_documentos_vision" in metrics
    assert isinstance(metrics["tiempo_promedio_respuesta_minutos"], (int, float))
