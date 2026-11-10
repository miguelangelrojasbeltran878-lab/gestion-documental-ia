"""Proveedor de IA con Plan B.

Proveedor principal: Google Gemini (nivel gratuito) mediante la librería oficial `google-genai`.
Plan B: si no hay clave, se agota la cuota, falla la red o la respuesta es inválida, se devuelve
`AIResult(ok=False, ...)` y quien llama usa su lógica local de respaldo (reglas). El sistema nunca
queda bloqueado por una falla del proveedor.
"""
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app import config

log = logging.getLogger("ai_provider")


@dataclass
class AIResult:
    ok: bool
    provider: str  # "gemini" | "local"
    text: str = ""
    data: Optional[Any] = None
    error: str = ""
    attempts: int = 0
    latency_ms: int = 0
    meta: dict = field(default_factory=dict)


_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai
        from google.genai import types
        _client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=int(config.AI_TIMEOUT_SECONDS * 1000)),
        )
    return _client


def is_available() -> bool:
    return bool(config.GEMINI_API_KEY) and config.AI_EXTERNAL_ALLOWED


def status() -> dict:
    if not config.GEMINI_API_KEY:
        return {"provider": "local", "available": False, "reason": "GEMINI_API_KEY no configurada: se usa Plan B (reglas locales)"}
    if not config.AI_EXTERNAL_ALLOWED:
        return {"provider": "local", "available": False, "reason": "AI_EXTERNAL_ALLOWED=false: procesamiento solo local"}
    return {"provider": "gemini", "available": True, "model": config.GEMINI_MODEL}


def _extract_json(text: str):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def generate(prompt: str, *, json_mode: bool = False, images: Optional[list] = None,
             system: Optional[str] = None, temperature: float = 0.2) -> AIResult:
    """Llama a Gemini. `images` = lista de (bytes, mime_type). Nunca lanza excepción."""
    if not is_available():
        return AIResult(ok=False, provider="local", error=status()["reason"])

    from google.genai import types

    parts: list = []
    for data, mime in images or []:
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    parts.append(prompt)

    cfg = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
        response_mime_type="application/json" if json_mode else None,
    )

    last_err = ""
    start = time.time()
    attempts = 0
    for attempt in range(1, config.AI_MAX_RETRIES + 2):
        attempts = attempt
        try:
            resp = _get_client().models.generate_content(model=config.GEMINI_MODEL, contents=parts, config=cfg)
            text = (resp.text or "").strip()
            if not text:
                raise ValueError("Respuesta vacía del modelo")
            data = _extract_json(text) if json_mode else None
            return AIResult(ok=True, provider="gemini", text=text, data=data, attempts=attempts,
                            latency_ms=int((time.time() - start) * 1000))
        except Exception as e:  # cuota (429), red, JSON inválido, etc.
            last_err = f"{type(e).__name__}: {str(e)[:300]}"
            log.warning("Gemini intento %s falló: %s", attempt, last_err)
            quota = "429" in last_err or "RESOURCE_EXHAUSTED" in last_err
            if attempt <= config.AI_MAX_RETRIES:
                time.sleep(min(2 ** attempt, 8) if quota else 1)
    return AIResult(ok=False, provider="local", error=last_err, attempts=attempts,
                    latency_ms=int((time.time() - start) * 1000))
