import os

models_path = r'c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo\app\models.py'
with open(models_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already added
if 'EjecucionAutomatizacion' not in content:
    content = content.replace(
        'empresa_organizacion = Column(String(150), nullable=True)\n    fecha_registro',
        'empresa_organizacion = Column(String(150), nullable=True)\n    acepta_tratamiento_datos = Column(Boolean, default=False)\n    fecha_autorizacion_datos = Column(DateTime, nullable=True)\n    fecha_registro'
    )
    content = content.replace(
        'rol = Column(String(50), default="Agente", nullable=False)\n    activo',
        'rol = Column(String(50), default="Agente", nullable=False)\n    password_hash = Column(String(255), nullable=True)\n    ultimo_acceso = Column(DateTime, nullable=True)\n    activo'
    )
    
    extra_models = '''

class EjecucionAutomatizacion(Base):
    """Registro de cada ejecución del motor de automatización propio (reemplazo de flujos externos)."""
    __tablename__ = "tbl_ejecucion_automatizacion"

    id_ejecucion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo_ejecucion = Column(String(40), unique=True, nullable=False, index=True)
    flujo = Column(String(80), nullable=False, index=True)
    proceso = Column(String(80), nullable=False, index=True)
    usuario = Column(String(120), nullable=True)
    id_ticket = Column(Integer, ForeignKey("tbl_ticket.id_ticket"), nullable=True, index=True)
    entrada_resumen = Column(Text, nullable=True)
    estado = Column(String(20), nullable=False, default="EN_CURSO")
    resultado = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    intentos = Column(Integer, default=0)
    proveedor_ia = Column(String(30), nullable=True)
    duracion_ms = Column(Integer, default=0)
    fecha_inicio = Column(DateTime, default=datetime.utcnow, index=True)
    fecha_fin = Column(DateTime, nullable=True)


class DocumentoVision(Base):
    """Documento/imagen procesado por el módulo de visión por computador."""
    __tablename__ = "tbl_documento_vision"

    id_documento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(30), unique=True, nullable=False, index=True)
    id_ticket = Column(Integer, ForeignKey("tbl_ticket.id_ticket"), nullable=True, index=True)
    nombre_original = Column(String(255), nullable=False)
    mime_type = Column(String(60), nullable=False)
    tamano_bytes = Column(Integer, default=0)
    sha256 = Column(String(64), index=True)
    ruta_archivo = Column(String(500), nullable=False)
    cargado_por = Column(String(120), nullable=True)
    tipo_documento = Column(String(60), nullable=True)
    repositorio = Column(String(80), nullable=True)
    texto_extraido = Column(Text, nullable=True)
    campos_json = Column(Text, nullable=True)
    campos_confirmados_json = Column(Text, nullable=True)
    confianza = Column(Float, nullable=True)
    proveedor = Column(String(30), nullable=True)
    estado = Column(String(30), default="RECIBIDO")
    error = Column(Text, nullable=True)
    revisado_por = Column(String(120), nullable=True)
    fecha_carga = Column(DateTime, default=datetime.utcnow)
    fecha_revision = Column(DateTime, nullable=True)
'''
    content += extra_models
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Models updated successfully!")
else:
    print("Models already contain EjecucionAutomatizacion.")
