# Spec: acceso seguro y primer corte de experiencia

## Objetivo

Convertir el portal existente en una aplicación que no exponga expedientes, lotes, documentos de visión ni operaciones administrativas a visitantes anónimos. El primer corte también corrige los mensajes y enlaces que presentan Make/n8n como una dependencia operativa, ya que el proyecto seguirá la Ruta A: automatización Python propia.

Éxito significa que los usuarios anónimos solo puedan crear y consultar sus propias solicitudes por código; los agentes autenticados vean únicamente los tickets que les corresponden; los administradores accedan a las vistas globales; y ningún archivo almacenado sea descargable sin autorización.

## Tecnologías y comandos

- Python 3.10+, FastAPI, SQLAlchemy, Jinja2 y pytest.
- Desarrollo: `cd 03_Desarrollo; python run.py`
- Pruebas: `cd 03_Desarrollo; python -m pytest test_suite.py -v`
- Compilación: `python -m compileall -q 03_Desarrollo/app 03_Desarrollo/test_suite.py`

## Estructura relevante

- `03_Desarrollo/app/auth.py`: sesión y dependencias de autorización.
- `03_Desarrollo/app/main.py`: páginas y API web.
- `03_Desarrollo/app/make_batch_router.py`: será renombrado funcionalmente de forma gradual, sin eliminar datos ni rutas aún usadas.
- `03_Desarrollo/app/templates/`: interfaz server-rendered.
- `03_Desarrollo/test_suite.py`: pruebas de integración actuales y nuevas pruebas de autorización.

## Criterios de aceptación

1. Las rutas de agente, administrador, visión y lotes requieren autenticación y el rol adecuado.
2. Los archivos adjuntos y documentos de visión no pueden descargarse, listarse ni confirmarse sin que el usuario tenga acceso al ticket/recurso.
3. Los endpoints de alta de tickets y consulta pública conservan su flujo sin exponer registros ajenos.
4. No quedan secretos por defecto ni URL de descarga que funcione sin token y autorización.
5. La interfaz principal describe “motor propio de automatización” y no promete n8n, Make, OpenAI, LangChain u OCR inexistentes.
6. Existen pruebas que cubren visitante, agente y administrador; el conjunto completo pasa.

## Estilo

Usar dependencias explícitas de FastAPI y funciones pequeñas orientadas al recurso:

```python
def require_ticket_access(ticket: models.Ticket, user: models.UsuarioAgente) -> None:
    if user.rol != "Administrador" and ticket.id_agente_asignado != user.id_agente:
        raise HTTPException(status_code=403, detail="No tiene acceso a este expediente.")
```

## Pruebas

- Añadir pruebas de 401/403 para cada operación sensible.
- Probar que un token faltante o inválido no devuelve archivos.
- Ejecutar la suite existente y una navegación local de las vistas públicas/autenticadas.

## Límites

- Siempre: preservar `tickets.db`, realizar copia antes de cualquier migración, guardar secretos solo en `.env` y usar valores seguros en producción.
- Preguntar antes: instalar un motor OCR o una nueva dependencia, cambiar el esquema de BD, introducir un proveedor externo o desplegar.
- Nunca: borrar registros, inventar resultados de IA/OCR, conservar una contraseña o secreto real en código/documentación.

## Fuera de alcance de este corte

- Sustituir SQLite por PostgreSQL.
- Instalar OCR o procesar las 20 fotografías reales.
- Reescribir todos los documentos Word; se actualizarán cuando haya evidencia de las implementaciones.
