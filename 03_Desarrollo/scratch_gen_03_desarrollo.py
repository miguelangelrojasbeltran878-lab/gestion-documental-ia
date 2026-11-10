import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, hex_color):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_styled_table(doc, headers, data, col_widths=None):
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1F497D")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.font.size = Pt(9)
            run.font.name = "Arial"

    for r_idx, row in enumerate(data):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = "F2F5F9" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            if c_idx == 0 or len(str(val)) < 15:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.size = Pt(8.5)
                run.font.name = "Arial"

    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = width

    doc.add_paragraph()
    return table

def add_header_footer(doc, title_text):
    for s in doc.sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)
        
        header = s.header
        hp = header.paragraphs[0]
        hp.text = f"SISTEMA INTELIGENTE DE GESTIÓN Y ANÁLISIS DOCUMENTAL — {title_text.upper()}"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if hp.runs:
            hp.runs[0].font.size = Pt(8)
            hp.runs[0].font.color.rgb = RGBColor(120, 120, 120)
            hp.runs[0].font.name = "Arial"

        footer = s.footer
        fp = footer.paragraphs[0]
        fp.text = "Desarrollo de Aplicaciones Empresariales — Tercer Corte (2026)"
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if fp.runs:
            fp.runs[0].font.size = Pt(8)
            fp.runs[0].font.color.rgb = RGBColor(120, 120, 120)
            fp.runs[0].font.name = "Arial"

def build_codigo_backend():
    doc = Document()
    add_header_footer(doc, "Arquitectura del Código y Backend")

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("ARQUITECTURA DEL CÓDIGO Y MANUAL DE DESARROLLO BACKEND\nTERCER CORTE: FASTAPI, AUTONOMÍA Y CRIPTOGRAFÍA")
    r_title.font.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(31, 73, 125)
    r_title.font.name = "Arial"

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Estructura de Paquetes, Servicios Desacoplados, Seguridad PBKDF2 y Tareas Asíncronas")
    r_sub.font.italic = True
    r_sub.font.size = Pt(11)
    r_sub.font.name = "Arial"
    doc.add_paragraph()

    h1 = doc.add_heading("1. ESTRUCTURA MODULAR DEL BACKEND", level=1)
    h1.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph(
        "El backend está implementado con el framework moderno FastAPI (Python 3.12+), seleccionado por su soporte nativo "
        "para asincronía (async/await), validación automática mediante Pydantic y documentación OpenAPI interactiva. "
        "La base de código sigue principios de responsabilidad única (SRP) y alta cohesión:"
    )

    modules_data = [
        ["app/config.py", "Centraliza la configuración mediante Pydantic Settings o lectura de .env, incluyendo GEMINI_API_KEY, SECRET_KEY, umbrales de visión y rutas de storage."],
        ["app/database.py", "Configura la conexión SQLAlchemy Engine y sessionmaker para la base de datos relacional SQLite (tickets.db)."],
        ["app/models.py", "Declara las entidades ORM: Cliente, Ticket, Archivo, Categoria, UsuarioAgente, EjecucionAutomatizacion y DocumentoVision."],
        ["app/schemas.py", "Define esquemas de validación Pydantic para entradas/salidas de la API y contratos de datos."],
        ["app/auth.py", "Gestiona la seguridad criptográfica: generación y verificación de contraseñas con PBKDF2-SHA256 (100.000 iteraciones) y sesiones firmadas con itsdangerous."],
        ["app/automation_engine.py", "Motor de automatización autónomo (Componente 1). Ejecuta tareas en segundo plano sin dependencias de n8n, registra logs de auditoría y calcula latencia."],
        ["app/vision_service.py", "Servicio de visión artificial multimodal (Componente 2). Interpreta documentos con Gemini 2.5 Flash o Plan B heurístico, evaluando scores y umbrales."],
        ["app/ai_provider.py", "Capa unificada de inteligencia artificial. Administra llamadas a Google Gemini 2.5 Flash con fallback automático ante fallos de red o cuota."],
        ["app/ai_module.py", "Motor del Chatbot contextual multi-archivo, integrando RAG ligero sobre el expediente del ticket."],
        ["app/crud.py", "Operaciones de base de datos y cálculo de métricas 100% reales para el Dashboard Bento."],
        ["app/main.py", "Punto de entrada de la aplicación. Configura rutas REST, middleware de sesiones, manejo de excepciones y montaje de plantillas Jinja2."]
    ]
    create_styled_table(doc, ["Módulo / Archivo", "Responsabilidad Arquitectónica"], modules_data, [Inches(2.2), Inches(4.8)])

    h2 = doc.add_heading("2. IMPLEMENTACIÓN DE SEGURIDAD CRIPTOGRÁFICA (OWASP TOP 10)", level=1)
    h2.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph(
        "En cumplimiento de los requerimientos de seguridad y protección de datos:\n"
        "1. Almacenamiento Seguro de Credenciales: Las contraseñas de los usuarios agentes nunca se almacenan en texto plano. Se emplea la función de derivación de claves PBKDF2 con algoritmo pseudoaleatorio HMAC-SHA256 y 100.000 iteraciones, añadiendo una sal criptográfica (salt) aleatoria de 16 bytes generada por el sistema operativo (`os.urandom(16)`).\n"
        "2. Manejo de Sesiones: Las sesiones de usuario se gestionan mediante cookies HTTP con flags `HttpOnly` (para mitigar ataques XSS) y `SameSite=Lax` (para mitigar CSRF), firmadas criptográficamente con `itsdangerous.URLSafeTimedSerializer` utilizando la clave maestra `SECRET_KEY`.\n"
        "3. Habeas Data y Consentimiento Informado: Se exige el consentimiento expreso del titular de los datos en cumplimiento de la Ley 1581 de 2012 antes de registrar clientes y radicar tickets, registrando fecha y hora exacta de autorización."
    )

    out_path = r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo\01_Arquitectura_del_Codigo_y_Backend.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}")

def build_ia_multimodal():
    doc = Document()
    add_header_footer(doc, "IA Multimodal y Automatización")

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("INGENIERÍA DE IA MULTIMODAL Y AUTOMATIZACIÓN AUTÓNOMA\nTERCER CORTE: COMPONENTES 1 Y 2 CON PLAN B RESILIENTE")
    r_title.font.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(31, 73, 125)
    r_title.font.name = "Arial"

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Modelos de Lenguaje, Visión por Computador, Prompts Estructurados y Heurística Offline")
    r_sub.font.italic = True
    r_sub.font.size = Pt(11)
    r_sub.font.name = "Arial"
    doc.add_paragraph()

    h1 = doc.add_heading("1. COMPONENTE 1: AUTOMATIZACIÓN PROPIA EN CÓDIGO (RUTA A)", level=1)
    h1.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph(
        "Para dar cumplimiento estricto a la Guía Oficial del Tercer Corte sin incurrir en dependencias de software propietario o SaaS, "
        "se diseñó el motor `AutomationEngine`. Este servicio se ejecuta de manera asíncrona mediante el mecanismo `BackgroundTasks` "
        "de FastAPI, garantizando que el usuario reciba respuesta HTTP inmediata mientras el procesamiento pesado ocurre en segundo plano."
    )
    doc.add_paragraph(
        "Cada ciclo de automatización:\n"
        "- Genera un UUID de trazabilidad único (`codigo_ejecucion`).\n"
        "- Mide con precisión de milisegundos (`latencia_ms`) el tiempo total de procesamiento.\n"
        "- Registra en la tabla `tbl_ejecucion_automatizacion` los payloads de entrada y salida en formato JSON.\n"
        "- En caso de excepción, captura el traceback del error, registra el estado 'FALLIDO' y ejecuta un reintento automático."
    )

    h2 = doc.add_heading("2. COMPONENTE 2: VISIÓN MULTIMODAL Y EXTRACCIÓN ESTRUCTURADA", level=1)
    h2.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph(
        "El servicio `VisionService` procesa documentos escaneados o fotografías tomadas directamente desde la cámara móvil. "
        "Se seleccionó como modelo primario Google Gemini 2.5 Flash, optimizado para inferencia multimodal de alta velocidad y bajo consumo de cuota."
    )
    doc.add_paragraph(
        "Contrato JSON de Extracción Obligatorio:\n"
        "{\n"
        "  \"tipo_documento\": \"FACTURA | RECIBO | CUENTA_COBRO | CEDULA | OTRO\",\n"
        "  \"emisor\": \"Nombre o Razón Social\",\n"
        "  \"nit\": \"Número de Identificación Tributaria\",\n"
        "  \"fecha\": \"YYYY-MM-DD\",\n"
        "  \"total\": 0.00,\n"
        "  \"moneda\": \"COP | USD\",\n"
        "  \"score_confianza\": 0.95,\n"
        "  \"observaciones\": \"Resumen de calidad del documento\"\n"
        "}"
    )

    h3 = doc.add_heading("3. VALIDACIÓN HUMANA (HUMAN-IN-THE-LOOP) Y PLAN B LOCAL", level=1)
    h3.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph(
        "La Guía Docente exige expresamente que los sistemas empresariales no operen a ciegas ante incertidumbres de la IA. "
        "Por esta razón, se establecieron dos salvaguardas arquitectónicas críticas:\n\n"
        "1. Regla de Revisión Humana: Si el `score_confianza` retornado por el modelo es inferior a 0.80 (80%), el sistema automáticamente "
        "marca `requiere_revision_humana = True` y establece el estado en 'PENDIENTE_REVISION'. La interfaz gráfica `/vision` despliega "
        "una alerta ámbar y un formulario prellenado para que un agente humano confirme o edite los campos antes de impactar los sistemas contables.\n\n"
        "2. Plan B Local Heurístico: Si el entorno carece de conexión a Internet, la API Key no está configurada o se excede la cuota de Google, "
        "el sistema activa de forma transparente el motor local de OCR heurístico. Este motor analiza el flujo de texto o patrones visuales sintácticos "
        "mediante expresiones regulares especializadas para NITs colombianos, fechas ISO y cifras numéricas monetarias, asegurando una disponibilidad "
        "operativa del 100% bajo cualquier contingencia."
    )

    out_path = r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo\02_IA_Multimodal_y_Automatizacion.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    os.makedirs(r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo", exist_ok=True)
    build_codigo_backend()
    build_ia_multimodal()
