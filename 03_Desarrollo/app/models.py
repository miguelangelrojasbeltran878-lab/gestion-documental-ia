from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Cliente(Base):
    __tablename__ = "tbl_cliente"

    id_cliente = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre_completo = Column(String(150), nullable=False)
    correo_electronico = Column(String(100), nullable=False, index=True)
    telefono = Column(String(20), nullable=True)
    empresa_organizacion = Column(String(150), nullable=True)
    acepta_tratamiento_datos = Column(Boolean, default=False)
    fecha_autorizacion_datos = Column(DateTime, nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    tickets = relationship("Ticket", back_populates="cliente")

class UsuarioAgente(Base):
    __tablename__ = "tbl_usuario_agente"

    id_agente = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre_completo = Column(String(150), nullable=False)
    correo_electronico = Column(String(100), unique=True, nullable=False)
    rol = Column(String(50), default="Agente", nullable=False)
    password_hash = Column(String(255), nullable=True)
    ultimo_acceso = Column(DateTime, nullable=True)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    tickets_asignados = relationship("Ticket", back_populates="agente_asignado")
    soluciones = relationship("Solucion", back_populates="autor")

class Ticket(Base):
    __tablename__ = "tbl_ticket"

    id_ticket = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo_seguimiento = Column(String(20), unique=True, nullable=False, index=True)
    id_cliente = Column(Integer, ForeignKey("tbl_cliente.id_cliente"), nullable=False)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=False)
    categoria_preliminar = Column(String(50), default="General")
    prioridad = Column(String(20), default="Media") # Alta, Media, Baja
    estado = Column(String(20), default="Abierto") # Abierto, En Proceso, Resuelto, Cerrado
    id_agente_asignado = Column(Integer, ForeignKey("tbl_usuario_agente.id_agente"), nullable=True)
    respuesta_oficial = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="tickets")
    agente_asignado = relationship("UsuarioAgente", back_populates="tickets_asignados")
    sugerencia_ia = relationship("SugerenciaIA", back_populates="ticket", uselist=False)
    lotes = relationship("LoteArchivos", back_populates="ticket", cascade="all, delete-orphan")
    mensajes = relationship("MensajeTicket", back_populates="ticket", cascade="all, delete-orphan", order_by="MensajeTicket.fecha_envio.asc()")
    calificacion = relationship("CalificacionTicket", back_populates="ticket", uselist=False, cascade="all, delete-orphan")

class SugerenciaIA(Base):
    __tablename__ = "tbl_sugerencia_ia"

    id_sugerencia = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_ticket = Column(Integer, ForeignKey("tbl_ticket.id_ticket"), unique=True, nullable=False)
    prioridad_sugerida = Column(String(20), nullable=False)
    categoria_sugerida = Column(String(50), nullable=True)
    respuesta_sugerida = Column(Text, nullable=False)
    score_confianza = Column(Float, default=0.95)
    fecha_analisis = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="sugerencia_ia")

class Solucion(Base):
    __tablename__ = "tbl_solucion"

    id_solucion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    titulo = Column(String(200), nullable=False)
    contenido_solucion = Column(Text, nullable=False)
    categoria = Column(String(50), nullable=False)
    palabras_clave = Column(String(255), nullable=True)
    id_ticket_origen = Column(Integer, ForeignKey("tbl_ticket.id_ticket"), nullable=True)
    id_autor = Column(Integer, ForeignKey("tbl_usuario_agente.id_agente"), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    autor = relationship("UsuarioAgente", back_populates="soluciones")

class LoteArchivos(Base):
    __tablename__ = "tbl_lote_archivos"

    id_lote = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_code = Column(String(30), unique=True, nullable=False, index=True)
    id_ticket = Column(Integer, ForeignKey("tbl_ticket.id_ticket"), nullable=False)
    estado_make = Column(String(30), default="QUEUED") # QUEUED, PROCESSING_IN_MAKE, COMPLETED, ERROR
    total_archivos = Column(Integer, default=0)
    archivos_procesados = Column(Integer, default=0)
    sintesis_global_ia = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_completado = Column(DateTime, nullable=True)

    ticket = relationship("Ticket", back_populates="lotes")
    archivos = relationship("ArchivoAdjunto", back_populates="lote", cascade="all, delete-orphan")

class ArchivoAdjunto(Base):
    __tablename__ = "tbl_archivo_adjunto"

    id_archivo = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_lote = Column(Integer, ForeignKey("tbl_lote_archivos.id_lote"), nullable=False)
    file_code = Column(String(20), nullable=False)
    nombre_original = Column(String(255), nullable=False)
    extension = Column(String(15), nullable=False)
    mime_type = Column(String(100), nullable=False)
    tamano_bytes = Column(Integer, default=0)
    ruta_temporal = Column(String(500), nullable=False)
    estado_procesamiento = Column(String(30), default="PENDING") # PENDING, PROCESSED, ERROR_UNREADABLE
    tipo_documento_ia = Column(String(100), nullable=True)
    resumen_extraido_ia = Column(Text, nullable=True)
    prioridad_detectada = Column(String(20), nullable=True)
    recomendacion_ia = Column(Text, nullable=True)
    score_confianza = Column(Float, default=0.95)

    lote = relationship("LoteArchivos", back_populates="archivos")

class MensajeTicket(Base):
    __tablename__ = "tbl_mensaje_ticket"

    id_mensaje = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_ticket = Column(Integer, ForeignKey("tbl_ticket.id_ticket"), nullable=False, index=True)
    remitente_tipo = Column(String(20), nullable=False) # CLIENTE, IA, AGENTE
    remitente_nombre = Column(String(150), nullable=False)
    contenido = Column(Text, nullable=False)
    fecha_envio = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="mensajes")

class CalificacionTicket(Base):
    __tablename__ = "tbl_calificacion_ticket"

    id_calificacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_ticket = Column(Integer, ForeignKey("tbl_ticket.id_ticket"), unique=True, nullable=False)
    estrellas = Column(Integer, nullable=False, default=5) # 1 a 5
    comentario = Column(Text, nullable=True)
    fecha_calificacion = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="calificacion")


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


class Gasto(Base):
    """Registro de compras/gastos creado automáticamente por el módulo de visión a partir de una factura o recibo."""
    __tablename__ = "tbl_gasto"

    id_gasto = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo_documento = Column(String(30), unique=True, nullable=False, index=True)  # VIS-...
    proveedor = Column(String(200), nullable=True)
    nit = Column(String(30), nullable=True, index=True)
    numero_documento = Column(String(60), nullable=True)
    fecha_documento = Column(String(10), nullable=True)
    monto_total = Column(Float, default=0.0)
    moneda = Column(String(5), default="COP")
    estado = Column(String(20), default="REGISTRADO")  # REGISTRADO | ANULADO
    registrado_por = Column(String(120), nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)


class AuditoriaIA(Base):
    """Bitácora de auditoría de acciones de la IA y de acceso a datos sensibles (quién, qué, cuándo)."""
    __tablename__ = "tbl_auditoria_ia"

    id_auditoria = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha = Column(DateTime, default=datetime.utcnow, index=True)
    usuario = Column(String(120), nullable=True, index=True)
    accion = Column(String(60), nullable=False, index=True)  # SUBIDA_IMAGEN, EXTRACCION_IA, CONFIRMACION, ACCESO_ARCHIVO...
    recurso = Column(String(80), nullable=True, index=True)
    proveedor = Column(String(30), nullable=True)
    detalle = Column(Text, nullable=True)
