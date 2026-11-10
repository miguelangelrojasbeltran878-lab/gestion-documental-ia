from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

# Cliente schemas
class ClienteBase(BaseModel):
    nombre_completo: str
    correo_electronico: str
    telefono: Optional[str] = None
    empresa_organizacion: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(ClienteBase):
    id_cliente: int
    fecha_registro: datetime
    class Config:
        from_attributes = True

# Ticket schemas
class TicketCreate(BaseModel):
    nombre_cliente: str
    correo_cliente: str
    telefono: Optional[str] = None
    empresa: Optional[str] = None
    titulo: str
    descripcion: str
    categoria_preliminar: Optional[str] = "General"

class TicketResponse(BaseModel):
    id_ticket: int
    codigo_seguimiento: str
    titulo: str
    descripcion: str
    categoria_preliminar: str
    prioridad: str
    estado: str
    respuesta_oficial: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    id_cliente: int
    id_agente_asignado: Optional[int] = None
    class Config:
        from_attributes = True

class TicketAsignar(BaseModel):
    id_agente: int

class TicketResponder(BaseModel):
    respuesta_oficial: str
    nuevo_estado: str = "Resuelto"

# IA schemas
class SugerenciaIAResponse(BaseModel):
    id_sugerencia: int
    id_ticket: int
    prioridad_sugerida: str
    categoria_sugerida: Optional[str] = None
    respuesta_sugerida: str
    score_confianza: float
    fecha_analisis: datetime
    class Config:
        from_attributes = True

# Solución schemas
class SolucionCreate(BaseModel):
    titulo: str
    contenido_solucion: str
    categoria: str
    palabras_clave: Optional[str] = None
    id_autor: int
    id_ticket_origen: Optional[int] = None

class SolucionResponse(BaseModel):
    id_solucion: int
    titulo: str
    contenido_solucion: str
    categoria: str
    palabras_clave: Optional[str] = None
    fecha_creacion: datetime
    id_autor: int
    id_ticket_origen: Optional[int] = None
    class Config:
        from_attributes = True
