"""
Impresión desde la bandeja de órdenes LIMS (no muta estado).

- Listado de órdenes del día (A4 apaisado).
- Pedidos en formato papel institucional:
  - clínico: lista solo los paneles/exámenes solicitados + Observaciones + Firma/Fecha;
  - microbiología: formulario de cultivos con cruz en los pedidos (incluye Obs./Firma).
  Un pedido por orden clínica y uno por paciente para microbiología
  (todos sus cultivos de la selección en el mismo pedido); 2 pedidos por hoja A4 apaisada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Iterable

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from auditoria.audit_service import log_event
from laboratorio.informe_pdf_config import INFORME_LAB_CONFIG, LABORATORIO_STATIC
from laboratorio.models import SolicitudExamen
from laboratorio.models_microbiologia import EstudioMicrobiologia
from laboratorio.resena_pedido import (
    ContextoResena,
    componentes_paneles_basicos,
    construir_resena_reglas,
    examenes_que_requieren_resena,
    recortar_antecedentes,
    sugerir_resenas,
)
from laboratorio.talon_pedido_pdf import _fmt_medico, _fmt_paciente

TIPO_LAB = "LAB_CLINICO"
TIPO_MICRO = "MICROBIOLOGIA"
MAX_ITEMS_IMPRESION = 300

CEHTA_LOGO = "cehta_logo.png"

# --- Formulario clínico (columna izquierda | derecha), textos tal cual el papel ---
# (etiqueta, tipo, código). tipo: "panel" | "examen" | None (sin casilla mapeada).
FORM_CLINICO_IZQ: list[tuple[str, str | None, str | None]] = [
    ("Hemograma", "panel", "PAN_HEMO"),
    ("Hemoglobina glicosilada (HbA1c)", "examen", "HBA1C"),
    ("Glucemia", "examen", "GLU"),
    ("Uremia", "examen", "UREA"),
    ("Creatininemia", "examen", "CREATI"),
    ("Uricemia", "examen", "AU"),
    ("Calcemia", "examen", "CA"),
    ("Magnesemia", "examen", "MG"),
    ("Fosfatemia", "examen", "P"),
    ("Ferremia", "examen", "FERR"),
    ("Ionograma plasmático", "panel", "PAN_IONO"),
    ("Cloro", "examen", "CL"),
    ("Calcio ionico", "examen", "CA_ION"),
    ("Perfil lipoprotéico", "panel", "PAN_LIP"),
    ("Hepatograma", "panel", "PAN_HEP"),
    ("Proteinemia", "examen", "PROT_T"),
    ("Albuminemia", "examen", "ALB"),
    ("Coagulograma Básico", "panel", "PAN_COAG"),
    ("R.I.N.", "examen", "INR"),
    ("Eritrosedimentación", "examen", "VSG"),
    ("Proteína C reactiva ultrasensible", "examen", "PCR_US"),
    ("Amilasa", "examen", "AMIL"),
    ("Lipasa", "examen", "LIP"),
    ("GGT", "examen", "GGT"),
    ("LDH", "examen", "LDH"),
    ("Test rápido HBsAg (Hepatitis B)", "examen", "HBVAGS"),
    ("Test rápido Hepatitis C", "examen", "HCVG"),
    ("Test rápido HIV", "examen", "HIVAC"),
    ("Gonadotrofina coriónica (β-HCG)", "examen", "HCGB"),
    ("Sangre oculta en materia fecal", "examen", "SANOC"),
    ("ASTO (Antiestreptolisina O)", "examen", "ASTO"),
    ("Grupo sanguíneo", "examen", "GRUPO"),
    ("Perfil Férrico", "panel", "PAN_FERR"),
]
FORM_CLINICO_DER: list[tuple[str, str | None, str | None]] = [
    ("CPK", "examen", "CPK"),
    ("CPK-MB", "examen", "CPK_MB"),
    ("Troponina I", "examen", "TROP_I"),
    ("Mioglobina", "examen", "MIOG"),
    ("Troponina I ultrasensible", "examen", "TROP_US"),
    ("Pro-BNP", "examen", "PROBNP"),
    ("Dimero D", "examen", "DDIM"),
    ("Orina Completa", "panel", "PAN_ORI"),
    ("Clearance de creatinina", "panel", "PAN_CLEAR"),
    ("Ionograma urinario 24hs", "panel", "PAN_IONO_U24"),
    ("Ionograma urinario al azar", "panel", "PAN_IONO_U"),
    ("Proteinuria 24hs", "panel", "PAN_PROT24"),
    ("Proteinuria al azar", "examen", "PROT_U_AZ"),
    ("Microalbuminuria 24hs", "panel", "PAN_MALB24"),
    ("Microalbuminuria al azar", "panel", "PAN_MALB_AZ"),
    ("Proteinograma electroforético", "panel", "PAN_ELP"),
    ("Lipoproteína A", "examen", "LPA"),
    ("PSA", "examen", "PSA"),
    ("TSH", "examen", "TSH"),
    ("T3", "examen", "T3"),
    ("T4", "examen", "T4"),
    ("T4L", "examen", "T4L"),
    ("Vitamina B12", "examen", "B12"),
    ("Vitamina D", "examen", "VITD"),
    ("EAB Arterial", "panel", "PAN_EAB_ART"),
    ("EAB Venoso", "panel", "PAN_EAB_VEN"),
    ("Acido Láctico / Lactato", "examen", "LACT"),
]

# Si el panel está pedido, estas casillas del papel también se marcan
# (aunque el analito no figure suelto fuera del panel).
_MARCAS_EXTRA_POR_PANEL: dict[str, frozenset[str]] = {
    "PAN_IONO": frozenset({"CL"}),
    "PAN_COAG": frozenset({"INR"}),
}

# --- Formulario microbiología: (etiqueta, códigos de TipoCultivoMicrobiologia) ---
MICRO_CULTIVO_DE = "__CULTIVO_DE__"
FORM_MICRO_IZQ: list[tuple[str, frozenset[str]]] = [
    ("Hemocultivo", frozenset({"HEMOCULTIVO"})),
    ("Cultivo Líquido pericárdico", frozenset({"LIQUIDO_PERICARDICO"})),
    ("Cultivo Líquido Mediastinal", frozenset()),
    ("Cultivo de líquido cefalorraquídeo", frozenset({"LCR"})),
    ("Cultivo de catéter", frozenset({"CATETER", "PUNTA_CATETER"})),
    ("Cultivo líquido pleural", frozenset({"LIQUIDO_PLEURAL"})),
    ("Cultivo de Líquido ascítico o peritoneal", frozenset({"LIQUIDO_PERITONEAL"})),
    ("Cultivo Líquido articular o sinovial", frozenset({"LIQUIDO_SINOVIAL"})),
    ("Cultivo muestras osteoarticulares", frozenset({"OSEO"})),
    ("Cultivo Aspirado Bronquial/Traqueal", frozenset({"ASPIRADO_TRAQUEAL_BRONQUIAL"})),
    ("Cultivo Lavados broncoalveolares", frozenset({"MINI_BAL"})),
    ("Cultivo Piel/Partes Blandas y Abscesos", frozenset({"PIEL_PARTES_BLANDAS", "HERIDA_ABSCESO"})),
    ("Cultivo Punción transtraqueal", frozenset()),
    ("Cultivo de:", frozenset({MICRO_CULTIVO_DE})),
]
FORM_MICRO_DER: list[tuple[str, frozenset[str]]] = [
    ("Urocultivo", frozenset({"UROCULTIVO"})),
    ("Esputo", frozenset({"ESPUTO"})),
    ("Baciloscopía de Esputo", frozenset()),
    ("Exudado de fauces", frozenset()),
    ("Exudado vaginal", frozenset({"VAGINAL", "SGB"})),
    ("Coprocultivo", frozenset({"COPROCULTIVO"})),
    ("Cultivo Hisopado Anal", frozenset({"HISOPADO_ANAL"})),
    ("Coproparasitológico", frozenset()),
    ("Antibiograma", frozenset()),
    ("Test Rápido HIV", frozenset()),
    ("Test Rápido HBsAg", frozenset()),
    ("Test Rápido COVID", frozenset()),
    ("Anticuerpos de:", frozenset()),
    ("PCR de:", frozenset()),
    ("Carga Viral de:", frozenset()),
]
_MICRO_CODIGOS_MAPEADOS = frozenset(
    c for _, cods in (*FORM_MICRO_IZQ, *FORM_MICRO_DER) for c in cods if c != MICRO_CULTIVO_DE
)


class ImpresionOrdenesError(ValueError):
    """Parámetros inválidos para impresión de órdenes."""


@dataclass
class ItemImpresion:
    tipo: str
    id: int


@dataclass
class DatosPedidoPapel:
    """Datos de cabecera comunes a ambos formularios."""

    paciente: str = ""
    dni: str = ""
    obra_social: str = ""
    afiliado: str = ""
    diagnostico: str = ""
    medico: str = ""
    fecha: str = ""
    numero: str = ""
    observaciones: str = ""
    sexo: str = ""
    edad: int | None = None
    antecedentes: str = ""


@dataclass
class PedidoClinicoPapel:
    datos: DatosPedidoPapel
    marcados: set[str] = field(default_factory=set)
    otros: list[str] = field(default_factory=list)
    # Nombres de paneles/exámenes sueltos solicitados (para el cuerpo del PDF).
    solicitados: list[str] = field(default_factory=list)
    solicitud_id: int | None = None
    resena_examenes: list[tuple[str, str]] = field(default_factory=list)

    @property
    def incluye_probnp(self) -> bool:
        return "PROBNP" in self.marcados


@dataclass
class PedidoMicroPapel:
    datos: DatosPedidoPapel
    marcados: set[str] = field(default_factory=set)
    cultivo_de: list[str] = field(default_factory=list)
    otros: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parseo / carga
# ---------------------------------------------------------------------------


def parsear_items(raw) -> list[ItemImpresion]:
    if not isinstance(raw, list) or not raw:
        raise ImpresionOrdenesError("Seleccioná al menos una orden para imprimir.")
    if len(raw) > MAX_ITEMS_IMPRESION:
        raise ImpresionOrdenesError(
            f"Máximo {MAX_ITEMS_IMPRESION} órdenes por impresión."
        )
    items: list[ItemImpresion] = []
    seen: set[tuple[str, int]] = set()
    for it in raw:
        if not isinstance(it, dict):
            raise ImpresionOrdenesError("Formato de órdenes inválido.")
        tipo = str(it.get("tipo") or "").strip().upper()
        if tipo not in (TIPO_LAB, TIPO_MICRO):
            raise ImpresionOrdenesError("Tipo de orden inválido.")
        try:
            pk = int(it.get("id"))
        except (TypeError, ValueError):
            raise ImpresionOrdenesError("Identificador de orden inválido.") from None
        if pk <= 0:
            raise ImpresionOrdenesError("Identificador de orden inválido.")
        key = (tipo, pk)
        if key in seen:
            continue
        seen.add(key)
        items.append(ItemImpresion(tipo=tipo, id=pk))
    return items


def _cargar_objetos(
    items: list[ItemImpresion],
) -> list[SolicitudExamen | EstudioMicrobiologia]:
    lab_ids = [i.id for i in items if i.tipo == TIPO_LAB]
    micro_ids = [i.id for i in items if i.tipo == TIPO_MICRO]
    labs = {
        s.pk: s
        for s in SolicitudExamen.objects.filter(pk__in=lab_ids)
        .select_related(
            "paciente",
            "medico_interno",
            "consulta_hc",
        )
        .prefetch_related(
            "tipos_examen",
            "paneles__tipos_examen",
            "consulta_hc__diagnosticos",
        )
    }
    micros = {
        e.pk: e
        for e in EstudioMicrobiologia.objects.filter(pk__in=micro_ids)
        .select_related(
            "paciente",
            "medico_interno",
            "tipo_cultivo",
            "tipo_muestra_micro",
            "consulta_hc",
            "solicitud__consulta_hc",
        )
        .prefetch_related("consulta_hc__diagnosticos")
    }
    out: list[SolicitudExamen | EstudioMicrobiologia] = []
    for it in items:
        obj = labs.get(it.id) if it.tipo == TIPO_LAB else micros.get(it.id)
        if obj is not None:
            out.append(obj)
    if not out:
        raise ImpresionOrdenesError("No se encontraron las órdenes seleccionadas.")
    return out


# ---------------------------------------------------------------------------
# Helpers de datos
# ---------------------------------------------------------------------------


def _fecha_corta(dt: datetime | date | None) -> str:
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        dt = timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date()
    return dt.strftime("%d/%m/%Y")


def _diagnostico_consulta(consulta) -> str:
    if consulta is None:
        return ""
    texto = (getattr(consulta, "diagnostico_presuntivo", None) or "").strip()
    if texto:
        return texto
    try:
        nombres = [
            (d.nombre_diagnostico or "").strip()
            for d in consulta.diagnosticos.all()
        ]
    except Exception:
        nombres = []
    return "; ".join(n for n in nombres if n)


def _datos_cabecera(obj, *, medico_externo: str = "") -> DatosPedidoPapel:
    paciente = getattr(obj, "paciente", None)
    nombre, dni = _fmt_paciente(paciente)
    medico = _fmt_medico(getattr(obj, "medico_interno", None), medico_externo)
    return DatosPedidoPapel(
        paciente=nombre if nombre != "—" else "",
        dni=dni if dni != "—" else "",
        obra_social=(getattr(paciente, "obra_social", None) or "").strip(),
        afiliado=(getattr(paciente, "numero_afiliado", None) or "").strip(),
        medico=medico if medico != "—" else "",
        numero=(getattr(obj, "numero", None) or "").strip(),
        observaciones=(getattr(obj, "observaciones", None) or "").strip(),
        sexo=(getattr(paciente, "sexo", None) or "").strip().upper(),
        edad=getattr(paciente, "edad", None) if paciente is not None else None,
        antecedentes=(getattr(paciente, "antecedentes_personales", None) or "").strip(),
    )


def _nombre_item(obj) -> str:
    return (getattr(obj, "nombre", None) or getattr(obj, "codigo", None) or "").strip()


def construir_pedido_clinico(
    sol: SolicitudExamen, *, componentes_basicos: set[str] | None = None
) -> PedidoClinicoPapel:
    from laboratorio.talon_pedido_pdf import _examenes_solicitud

    datos = _datos_cabecera(sol, medico_externo=sol.medico_externo_nombre or "")
    datos.diagnostico = _diagnostico_consulta(sol.consulta_hc)
    datos.fecha = _fecha_corta(sol.fecha_solicitud)

    codigos_form = {c for _, _, c in (*FORM_CLINICO_IZQ, *FORM_CLINICO_DER) if c}
    paneles = list(sol.paneles.all())
    componentes_panel: set[int] = set()
    for pan in paneles:
        componentes_panel.update(te.pk for te in pan.tipos_examen.all())

    marcados: set[str] = set()
    otros: list[str] = []
    for pan in sorted(paneles, key=lambda p: (p.nombre or "")):
        if pan.codigo in codigos_form:
            marcados.add(pan.codigo)
            marcados.update(_MARCAS_EXTRA_POR_PANEL.get(pan.codigo, ()))
        else:
            n = _nombre_item(pan)
            if n:
                otros.append(n)
    for te in sorted(sol.tipos_examen.all(), key=lambda t: (t.nombre or "")):
        if te.pk in componentes_panel:
            continue
        if te.codigo in codigos_form:
            marcados.add(te.codigo)
        else:
            n = _nombre_item(te)
            if n and n not in otros:
                otros.append(n)
    return PedidoClinicoPapel(
        datos=datos,
        marcados=marcados,
        otros=otros,
        solicitados=_examenes_solicitud(sol),
        solicitud_id=sol.pk,
        resena_examenes=examenes_que_requieren_resena(sol, componentes_basicos=componentes_basicos),
    )


def _sin_prefijo_cultivo(nombre: str) -> str:
    n = (nombre or "").strip()
    for pref in ("Cultivo de ", "Cultivo "):
        if n.lower().startswith(pref.lower()):
            return n[len(pref):].strip()
    return n


def construir_pedido_micro(estudios: list[EstudioMicrobiologia]) -> PedidoMicroPapel:
    """Una hoja por paciente con todos sus cultivos seleccionados."""
    base = estudios[0]
    datos = _datos_cabecera(base, medico_externo=base.medico_externo_nombre or "")
    consulta = base.consulta_hc
    if consulta is None and base.solicitud_id:
        consulta = base.solicitud.consulta_hc
    datos.diagnostico = _diagnostico_consulta(consulta)
    fechas = [e.created_at for e in estudios if e.created_at]
    datos.fecha = _fecha_corta(min(fechas) if fechas else None)
    numeros = [e.numero for e in estudios if e.numero]
    datos.numero = " / ".join(numeros)
    obs = []
    for e in estudios:
        o = (e.observaciones or "").strip()
        if o and o not in obs:
            obs.append(o)
    datos.observaciones = "\n".join(obs)

    marcados: set[str] = set()
    cultivo_de: list[str] = []
    otros: list[str] = []
    for e in estudios:
        tc = e.tipo_cultivo if e.tipo_cultivo_id else None
        if tc is not None:
            if tc.codigo in _MICRO_CODIGOS_MAPEADOS:
                marcados.add(tc.codigo)
            else:
                n = _sin_prefijo_cultivo(tc.nombre or tc.codigo)
                if n and n not in cultivo_de:
                    cultivo_de.append(n)
            continue
        libre = (e.tipo_estudio or "").strip()
        if libre and libre not in otros:
            otros.append(libre)
    if cultivo_de:
        marcados.add(MICRO_CULTIVO_DE)
    return PedidoMicroPapel(datos=datos, marcados=marcados, cultivo_de=cultivo_de, otros=otros)


def _pedidos_en_orden(objs) -> list[PedidoClinicoPapel | PedidoMicroPapel]:
    """Respeta el orden de la selección; micro se agrupa por paciente."""
    pedidos: list[PedidoClinicoPapel | PedidoMicroPapel] = []
    componentes_basicos = (
        componentes_paneles_basicos() if any(isinstance(o, SolicitudExamen) for o in objs) else set()
    )
    micro_por_paciente: dict[int, list[EstudioMicrobiologia]] = {}
    slots: list[tuple[str, object]] = []
    for obj in objs:
        if isinstance(obj, SolicitudExamen):
            slots.append(("lab", obj))
        else:
            grupo = micro_por_paciente.get(obj.paciente_id)
            if grupo is None:
                grupo = []
                micro_por_paciente[obj.paciente_id] = grupo
                slots.append(("micro", grupo))
            grupo.append(obj)
    for kind, val in slots:
        if kind == "lab":
            pedidos.append(
                construir_pedido_clinico(val, componentes_basicos=componentes_basicos)  # type: ignore[arg-type]
            )
        else:
            pedidos.append(construir_pedido_micro(val))  # type: ignore[arg-type]
    return pedidos


def _contexto_resena(ped: PedidoClinicoPapel) -> ContextoResena:
    d = ped.datos
    return ContextoResena(
        sexo=d.sexo if d.sexo in ("M", "F") else "",
        edad=d.edad,
        antecedentes=d.antecedentes,
        diagnostico=d.diagnostico,
        examenes=list(ped.resena_examenes),
    )


def resenas_sugeridas(items: list[ItemImpresion], *, prefer_medgemma: bool = True) -> list[dict]:
    """Sugerencias de reseña para las órdenes clínicas que la requieren (no persiste)."""
    pedidos = [
        p for p in _pedidos_en_orden(_cargar_objetos(items))
        if isinstance(p, PedidoClinicoPapel) and p.resena_examenes
    ]
    sugerencias = sugerir_resenas(
        [_contexto_resena(p) for p in pedidos], prefer_medgemma=prefer_medgemma
    )
    return [
        {
            "solicitud_id": p.solicitud_id,
            "numero": p.datos.numero,
            "paciente": p.datos.paciente,
            "examenes": [n for _, n in p.resena_examenes],
            "texto": s["texto"],
            "fuente": s["fuente"],
        }
        for p, s in zip(pedidos, sugerencias)
    ]


MAX_LARGO_RESENA = 2000


def parsear_resenas(raw) -> dict[int, str]:
    """{solicitud_id: texto} editado por el operador. Ausente => se usa la plantilla."""
    if raw in (None, ""):
        return {}
    if not isinstance(raw, list):
        raise ImpresionOrdenesError("Formato de reseñas inválido.")
    out: dict[int, str] = {}
    for it in raw:
        if not isinstance(it, dict):
            raise ImpresionOrdenesError("Formato de reseñas inválido.")
        try:
            pk = int(it.get("solicitud_id"))
        except (TypeError, ValueError):
            raise ImpresionOrdenesError("Reseña con orden inválida.") from None
        texto = str(it.get("texto") or "").strip()
        if len(texto) > MAX_LARGO_RESENA:
            raise ImpresionOrdenesError(f"La reseña supera los {MAX_LARGO_RESENA} caracteres.")
        out[pk] = texto
    return out


# ---------------------------------------------------------------------------
# Dibujo del formulario papel
# ---------------------------------------------------------------------------

PAGE_W, PAGE_H = A4
FONT = "Helvetica"
FONT_B = "Helvetica-Bold"
COLOR_TEXTO = colors.black
COLOR_DATO = colors.HexColor("#0B2E6F")
COLOR_CRUZ = colors.HexColor("#0B2E6F")
MARGEN_X = 14 * mm
DERECHA_X = PAGE_W - 14 * mm


def _y(top_mm: float) -> float:
    """Convierte distancia desde el borde superior (mm) a coordenada ReportLab."""
    return PAGE_H - top_mm * mm


def _ajustar_texto(c: rl_canvas.Canvas, texto: str, font: str, size: float, max_w: float) -> str:
    t = (texto or "").strip()
    if c.stringWidth(t, font, size) <= max_w:
        return t
    while t and c.stringWidth(t + "…", font, size) > max_w:
        t = t[:-1]
    return (t + "…") if t else ""


def _partir_lineas(c: rl_canvas.Canvas, texto: str, font: str, size: float, max_w: float) -> list[str]:
    lineas: list[str] = []
    for parrafo in (texto or "").splitlines():
        palabras = parrafo.split()
        actual = ""
        for p in palabras:
            prueba = f"{actual} {p}".strip()
            if c.stringWidth(prueba, font, size) <= max_w:
                actual = prueba
            else:
                if actual:
                    lineas.append(actual)
                actual = p
        if actual:
            lineas.append(actual)
    return lineas


def _linea_punteada(c: rl_canvas.Canvas, x1: float, x2: float, y: float) -> None:
    c.saveState()
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.setDash(0.6, 1.2)
    c.line(x1, y, x2, y)
    c.restoreState()


def _dibujar_logo_icpl(
    c: rl_canvas.Canvas, x: float, top_mm: float, w: float, h: float, *, anchor: str = "w"
) -> None:
    path = LABORATORIO_STATIC / (INFORME_LAB_CONFIG.get("logo") or "icpl_logo.png")
    if path.is_file():
        try:
            c.drawImage(
                ImageReader(str(path)),
                x,
                _y(top_mm) - h,
                width=w,
                height=h,
                preserveAspectRatio=True,
                anchor=anchor,
                mask="auto",
            )
            return
        except Exception:
            pass
    c.setFont(FONT_B, 10)
    if anchor == "c":
        c.drawCentredString(x + w / 2, _y(top_mm) - h / 2, "PUEBLO DE LUIS")
    else:
        c.drawString(x, _y(top_mm) - h / 2, "PUEBLO DE LUIS")


def _dibujar_logo_cehta(c: rl_canvas.Canvas, right_x: float, top_mm: float, w: float, h: float) -> None:
    path = LABORATORIO_STATIC / CEHTA_LOGO
    if path.is_file():
        try:
            c.drawImage(
                ImageReader(str(path)),
                right_x - w,
                _y(top_mm) - h,
                width=w,
                height=h,
                preserveAspectRatio=True,
                anchor="e",
                mask="auto",
            )
            return
        except Exception:
            pass
    # Logotipo vectorial (sin archivo de imagen disponible).
    rojo = colors.HexColor("#B3122E")
    azul = colors.HexColor("#1F3A6E")
    x0 = right_x - w
    base = _y(top_mm)
    c.saveState()
    c.setFillColor(rojo)
    c.setFont("Times-Bold", 17)
    c.drawString(x0, base - 6.2 * mm, "CEHTA")
    ancho_cehta = c.stringWidth("CEHTA", "Times-Bold", 17)
    c.setFont(FONT_B, 7.2)
    c.drawString(x0, base - 9.4 * mm, "CARDIOVASCULAR")
    c.setFillColor(azul)
    c.setFont(FONT, 4.2)
    c.drawString(x0, base - 11.6 * mm, "CENTRO DE HIPERTENSIÓN ARTERIAL")
    c.drawString(x0, base - 13.3 * mm, "Y ENFERMEDADES CARDIOVASCULARES")
    # Corazón con trazo de pulso.
    hx = x0 + ancho_cehta + 2.5 * mm
    hy = base - 5.5 * mm
    c.setStrokeColor(rojo)
    c.setLineWidth(1.1)
    p = c.beginPath()
    p.moveTo(hx + 4 * mm, hy - 5 * mm)
    p.curveTo(hx - 1 * mm, hy - 1.5 * mm, hx + 0.5 * mm, hy + 3.2 * mm, hx + 4 * mm, hy + 1 * mm)
    p.curveTo(hx + 7.5 * mm, hy + 3.2 * mm, hx + 9 * mm, hy - 1.5 * mm, hx + 4 * mm, hy - 5 * mm)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeColor(azul)
    c.setLineWidth(0.7)
    c.line(hx - 1 * mm, hy - 1.2 * mm, hx + 2 * mm, hy - 1.2 * mm)
    c.line(hx + 2 * mm, hy - 1.2 * mm, hx + 3 * mm, hy + 1.5 * mm)
    c.line(hx + 3 * mm, hy + 1.5 * mm, hx + 4.2 * mm, hy - 3 * mm)
    c.line(hx + 4.2 * mm, hy - 3 * mm, hx + 5 * mm, hy - 1.2 * mm)
    c.line(hx + 5 * mm, hy - 1.2 * mm, hx + 10.5 * mm, hy - 1.2 * mm)
    c.restoreState()


def _encabezado(c: rl_canvas.Canvas, subtitulo: str | None, numero: str) -> None:
    _dibujar_logo_icpl(c, MARGEN_X, 6, 42 * mm, 17 * mm)
    _dibujar_logo_cehta(c, DERECHA_X, 7.5, 46 * mm, 15 * mm)

    cx = PAGE_W / 2
    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT_B, 13)
    titulo = "LABORATORIO"
    y_t = _y(16)
    c.drawCentredString(cx, y_t, titulo)
    tw = c.stringWidth(titulo, FONT_B, 13)
    c.setLineWidth(0.9)
    c.line(cx - tw / 2, y_t - 1.3, cx + tw / 2, y_t - 1.3)
    if subtitulo:
        c.setFont(FONT_B, 9)
        y_s = _y(21.5)
        c.drawCentredString(cx, y_s, subtitulo)
        sw = c.stringWidth(subtitulo, FONT_B, 9)
        c.setLineWidth(0.7)
        c.line(cx - sw / 2, y_s - 1.1, cx + sw / 2, y_s - 1.1)
    if numero:
        c.setFont(FONT, 7)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawCentredString(cx, _y(25.5 if subtitulo else 21), f"Pedido {numero}")
        c.setFillColor(COLOR_TEXTO)


def _campo(c: rl_canvas.Canvas, x: float, top_mm: float, etiqueta: str, valor: str, max_x: float) -> None:
    size = 11.5
    y = _y(top_mm)
    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT, size)
    c.drawString(x, y, etiqueta)
    if valor:
        vx = x + c.stringWidth(etiqueta, FONT, size) + 2 * mm
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT_B, 10.5)
        c.drawString(vx, y, _ajustar_texto(c, valor, FONT_B, 10.5, max_x - vx - 1 * mm))
        c.setFillColor(COLOR_TEXTO)


def _cruz(c: rl_canvas.Canvas, x: float, y_bottom: float, w: float, h: float) -> None:
    inset_x = w * 0.2
    inset_y = h * 0.16
    c.saveState()
    c.setStrokeColor(COLOR_CRUZ)
    c.setLineWidth(1.7)
    c.setLineCap(1)
    c.line(x + inset_x, y_bottom + inset_y, x + w - inset_x, y_bottom + h - inset_y)
    c.line(x + inset_x, y_bottom + h - inset_y, x + w - inset_x, y_bottom + inset_y)
    c.restoreState()


def _columna_items(
    c: rl_canvas.Canvas,
    *,
    filas: list[tuple[str, bool, str]],
    label_x: float,
    box_x: float,
    box_w: float,
    top_mm: float,
    row_h_mm: float,
    size: float,
) -> None:
    """filas: (etiqueta, marcado, texto adicional escrito a mano)."""
    row_h = row_h_mm * mm
    for i, (etiqueta, marcado, extra) in enumerate(filas):
        top = _y(top_mm + i * row_h_mm)
        bottom = top - row_h
        base = bottom + row_h * 0.27
        c.setFillColor(COLOR_TEXTO)
        c.setFont(FONT, size)
        texto = f"- {etiqueta}"
        c.drawString(label_x, base, texto)
        if extra:
            ex = label_x + c.stringWidth(texto, FONT, size) + 1.5 * mm
            c.setFillColor(COLOR_DATO)
            c.setFont(FONT_B, size - 1.5)
            c.drawString(ex, base, _ajustar_texto(c, extra, FONT_B, size - 1.5, box_x - ex - 1 * mm))
            c.setFillColor(COLOR_TEXTO)
        _linea_punteada(c, label_x, box_x, bottom)
        c.setLineWidth(0.9)
        c.setStrokeColor(colors.black)
        c.rect(box_x, bottom, box_w, row_h, stroke=1, fill=0)
        if marcado:
            _cruz(c, box_x, bottom, box_w, row_h)


def _pie_firma(c: rl_canvas.Canvas, top_mm: float, medico: str, fecha: str) -> None:
    y = _y(top_mm)
    firma_cx = MARGEN_X + 38 * mm
    if medico:
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT_B, 9.5)
        c.drawCentredString(firma_cx, y + 6 * mm, _ajustar_texto(c, medico, FONT_B, 9.5, 80 * mm))
    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT, 11.5)
    c.drawCentredString(firma_cx, y, "Firma/Sello")
    fx = MARGEN_X + 92 * mm
    c.drawString(fx, y, "Fecha:")
    if fecha:
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT_B, 10.5)
        c.drawString(fx + c.stringWidth("Fecha:", FONT, 11.5) + 2 * mm, y, fecha)
        c.setFillColor(COLOR_TEXTO)


def _dibujar_pedido_clinico(c: rl_canvas.Canvas, ped: PedidoClinicoPapel) -> None:
    """Lista solo lo solicitado; reserva Observaciones + Firma/Fecha abajo."""
    d = ped.datos
    _encabezado(c, None, d.numero)
    col2 = MARGEN_X + 92 * mm
    _campo(c, MARGEN_X, 33, "Paciente:", d.paciente, col2 - 2 * mm)
    _campo(c, col2, 33, "DNI:", d.dni, DERECHA_X)
    _campo(c, MARGEN_X, 45, "Obra Social:", d.obra_social, col2 - 2 * mm)
    _campo(c, col2, 45, "N°Afiliado:", d.afiliado, DERECHA_X)
    _campo(c, MARGEN_X, 51, "Diagnóstico:", d.diagnostico, DERECHA_X)

    # Zonas fijas (mm desde arriba): lista → observaciones → firma.
    firma_top = 268.0
    obs_top = firma_top - 42.0
    titulo_top = 58.0
    lista_top = 66.0

    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT_B, 11.5)
    c.drawString(MARGEN_X, _y(titulo_top), "Exámenes solicitados:")

    items = list(ped.solicitados)
    if not items:
        c.setFont(FONT, 10.5)
        c.setFillColor(COLOR_DATO)
        c.drawString(MARGEN_X, _y(lista_top), "— Sin exámenes —")
        c.setFillColor(COLOR_TEXTO)
    else:
        max_h = max(obs_top - lista_top - 4.0, 24.0)
        rows_per_col = (len(items) + 1) // 2
        row_h = min(7.2, max(4.0, max_h / max(rows_per_col, 1)))
        if row_h >= 6.2:
            size = 11.0
        elif row_h >= 5.0:
            size = 10.0
        else:
            size = 9.0
        col_w = (DERECHA_X - MARGEN_X) / 2 - 2 * mm
        row_h_pt = row_h * mm
        for i, nombre in enumerate(items):
            col = 0 if i < rows_per_col else 1
            row = i if col == 0 else i - rows_per_col
            x = MARGEN_X if col == 0 else col2
            top = _y(lista_top + row * row_h)
            base = top - row_h_pt + row_h_pt * 0.27
            c.setFillColor(COLOR_TEXTO)
            c.setFont(FONT, size)
            etiqueta = f"- {_ajustar_texto(c, nombre, FONT, size, col_w)}"
            c.drawString(x, base, etiqueta)

    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT, 11.5)
    c.drawString(MARGEN_X, _y(obs_top), "Observaciones:")
    lineas_obs = [obs_top + 7 + i * 6.5 for i in range(4)]
    if d.observaciones:
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT_B, 10)
        for i, txt in enumerate(
            _partir_lineas(c, d.observaciones, FONT_B, 10, DERECHA_X - MARGEN_X)[:4]
        ):
            c.drawString(MARGEN_X, _y(lineas_obs[i]) + 1.2 * mm, txt)
        c.setFillColor(COLOR_TEXTO)
    for y_mm in lineas_obs:
        _linea_punteada(c, MARGEN_X, DERECHA_X, _y(y_mm))

    _pie_firma(c, firma_top, d.medico, d.fecha)


def _dibujar_pedido_micro(c: rl_canvas.Canvas, ped: PedidoMicroPapel) -> None:
    d = ped.datos
    _encabezado(c, "MICROBIOLOGÍA", d.numero)
    col2 = MARGEN_X + 92 * mm
    col3 = MARGEN_X + 131 * mm
    _campo(c, MARGEN_X, 36, "Paciente:", d.paciente, col2 - 2 * mm)
    _campo(c, col2, 36, "DNI:", d.dni, col3 - 2 * mm)
    _campo(c, col3, 36, "N° Afiliado:", d.afiliado, DERECHA_X)
    _campo(c, MARGEN_X, 49, "Obra Social:", d.obra_social, col2 - 2 * mm)
    _campo(c, col2, 49, "Diagnóstico:", d.diagnostico, DERECHA_X)
    _campo(c, MARGEN_X, 63, "Tratamiento iniciado: Si / No", "", DERECHA_X)
    _campo(c, MARGEN_X, 77, "Antibióticos:", "", DERECHA_X)

    top = 85.0
    row_h = 6.75
    size = 11.0
    box_w = 8.5 * mm
    cultivo_de_txt = ", ".join(ped.cultivo_de)
    izq = []
    for lbl, cods in FORM_MICRO_IZQ:
        marcado = any(cd in ped.marcados for cd in cods)
        extra = cultivo_de_txt if MICRO_CULTIVO_DE in cods else ""
        izq.append((lbl, marcado, extra))
    der = [(lbl, any(cd in ped.marcados for cd in cods), "") for lbl, cods in FORM_MICRO_DER]
    box_izq = MARGEN_X + 90 * mm
    col_der = box_izq + box_w + 5 * mm
    _columna_items(
        c, filas=izq, label_x=MARGEN_X, box_x=box_izq, box_w=box_w,
        top_mm=top, row_h_mm=row_h, size=size,
    )
    _columna_items(
        c, filas=der, label_x=col_der, box_x=DERECHA_X - box_w, box_w=box_w,
        top_mm=top, row_h_mm=row_h, size=size,
    )

    fin = top + row_h * len(izq)
    y_otro = fin + row_h
    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT, size)
    c.drawString(MARGEN_X, _y(y_otro) + row_h * mm * 0.27, "- Otro:")
    _linea_punteada(c, MARGEN_X, DERECHA_X, _y(y_otro))
    otros_txt = ", ".join(ped.otros)
    lineas_extra = [y_otro + 7, y_otro + 14]
    if otros_txt:
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT_B, 10)
        primera_x = MARGEN_X + c.stringWidth("- Otro:", FONT, size) + 2 * mm
        lineas = _partir_lineas(c, otros_txt, FONT_B, 10, DERECHA_X - primera_x - 1 * mm)
        if lineas:
            c.drawString(primera_x, _y(y_otro) + row_h * mm * 0.27, lineas[0])
        for y_mm, txt in zip(lineas_extra, lineas[1:]):
            c.drawString(MARGEN_X + 1 * mm, _y(y_mm) + 1.2 * mm, txt)
        c.setFillColor(COLOR_TEXTO)
    for y_mm in lineas_extra:
        _linea_punteada(c, MARGEN_X, DERECHA_X, _y(y_mm))

    y_obs = y_otro + 27
    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT, 11.5)
    c.drawString(MARGEN_X, _y(y_obs), "Observaciones:")
    if d.observaciones:
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT_B, 10)
        lineas = _partir_lineas(c, d.observaciones, FONT_B, 10, DERECHA_X - MARGEN_X)
        for i, txt in enumerate(lineas[:4]):
            c.drawString(MARGEN_X, _y(y_obs + 6 + i * 5), txt)
        c.setFillColor(COLOR_TEXTO)

    _pie_firma(c, y_obs + 40, d.medico, d.fecha)


PEDIDOS_POR_HOJA = 2


def _linea_corte(c: rl_canvas.Canvas, x: float, alto: float) -> None:
    c.saveState()
    c.setStrokeColor(colors.HexColor("#9AA0A6"))
    c.setLineWidth(0.4)
    c.setDash(2, 2.5)
    c.line(x, 4 * mm, x, alto - 4 * mm)
    c.restoreState()


# --- Formularios adjuntos (proBNP y reseña). Coordenadas A4 vertical; se imprimen
# reducidos a A5, por eso los cuerpos de letra son mayores que en el pedido. ---

FS_ADJ = 16.5
FS_ADJ_DATO = 15.5
ADJ_X = 24 * mm
ADJ_DERECHA = PAGE_W - 24 * mm
TEXTO_PROBNP_JUSTIFICACION = (
    "Ingresa a internación con signos de congestión al examen físico. Ante la sospecha "
    "de Insuficiencia Cardíaca Descompensada se solicita PRO BNP"
)


def _marco(c: rl_canvas.Canvas) -> None:
    c.saveState()
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.1)
    c.rect(12 * mm, 12 * mm, PAGE_W - 24 * mm, PAGE_H - 24 * mm, stroke=1, fill=0)
    c.restoreState()


def _logo_centrado(c: rl_canvas.Canvas, top_mm: float) -> None:
    w, h = 110 * mm, 46 * mm
    _dibujar_logo_icpl(c, (PAGE_W - w) / 2, top_mm, w, h, anchor="c")


def _campo_adj(c: rl_canvas.Canvas, top_mm: float, etiqueta: str, valor: str, *, x: float = ADJ_X) -> None:
    y = _y(top_mm)
    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT, FS_ADJ)
    c.drawString(x, y, etiqueta)
    if valor:
        vx = x + c.stringWidth(etiqueta, FONT, FS_ADJ) + 2.5 * mm
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT_B, FS_ADJ_DATO)
        c.drawString(vx, y, _ajustar_texto(c, valor, FONT_B, FS_ADJ_DATO, ADJ_DERECHA - vx))
        c.setFillColor(COLOR_TEXTO)


def _firma_y_sello_adj(c: rl_canvas.Canvas, top_mm: float) -> None:
    y = _y(top_mm)
    etiqueta = "Firma y sello:"
    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT, FS_ADJ)
    c.drawString(ADJ_X, y, etiqueta)
    x0 = ADJ_X + c.stringWidth(etiqueta, FONT, FS_ADJ) + 2 * mm
    c.setLineWidth(0.8)
    c.line(x0, y - 1, x0 + 85 * mm, y - 1)


def _fecha_adj(c: rl_canvas.Canvas, top_mm: float, fecha: str) -> None:
    _campo_adj(c, top_mm, "Fecha:", fecha)


def _dibujar_probnp_solicitud(c: rl_canvas.Canvas, d: DatosPedidoPapel) -> None:
    _marco(c)
    _logo_centrado(c, 24)
    _campo_adj(c, 92, "Nombre y apellido:", d.paciente)
    _campo_adj(c, 105, "DNI:", d.dni)
    _campo_adj(c, 118, "OS:", d.obra_social)
    c.setFont(FONT_B, 19)
    c.drawCentredString(PAGE_W / 2, _y(142), "SOLICITO proBNP")
    _firma_y_sello_adj(c, 182)
    _fecha_adj(c, 199, d.fecha)
    _campo_adj(c, 226, "Dx:", d.diagnostico)


def _dibujar_probnp_justificacion(c: rl_canvas.Canvas, d: DatosPedidoPapel) -> None:
    _marco(c)
    _logo_centrado(c, 20)
    _campo_adj(c, 86, "Nombre y apellido:", d.paciente)
    _campo_adj(c, 99, "DNI:", d.dni)
    _campo_adj(c, 112, "OS:", d.obra_social)

    y = _y(129)
    piezas = [("Paciente ", ""), ("femenina", "F"), ("/", ""), ("masculino", "M"),
              (" con antecedentes de", "")]
    x = ADJ_X
    c.setFont(FONT, FS_ADJ)
    c.setFillColor(COLOR_TEXTO)
    for txt, sexo in piezas:
        c.drawString(x, y, txt)
        w = c.stringWidth(txt, FONT, FS_ADJ)
        if sexo and sexo == d.sexo:
            c.setStrokeColor(COLOR_DATO)
            c.setLineWidth(1.3)
            c.line(x, y - 2, x + w, y - 2)
            c.setStrokeColor(colors.black)
        x += w

    lineas_ant = [141, 152]
    antecedentes = recortar_antecedentes(d.antecedentes, max_len=140)
    if antecedentes:
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT_B, FS_ADJ_DATO - 1)
        partes = _partir_lineas(c, antecedentes, FONT_B, FS_ADJ_DATO - 1, ADJ_DERECHA - ADJ_X - 2 * mm)
        for y_mm, txt in zip(lineas_ant, partes):
            c.drawString(ADJ_X + 1 * mm, _y(y_mm) + 1.5 * mm, txt)
        c.setFillColor(COLOR_TEXTO)
    for y_mm in lineas_ant:
        _linea_punteada(c, ADJ_X, ADJ_DERECHA, _y(y_mm))

    c.setFont(FONT, FS_ADJ)
    for i, txt in enumerate(
        _partir_lineas(c, TEXTO_PROBNP_JUSTIFICACION, FONT, FS_ADJ, ADJ_DERECHA - ADJ_X)
    ):
        c.drawString(ADJ_X, _y(166 + i * 8.6), txt)

    _firma_y_sello_adj(c, 212)
    _fecha_adj(c, 229, d.fecha)
    _campo_adj(c, 252, "Dx:", d.diagnostico)


def _dibujar_resena(c: rl_canvas.Canvas, ped: PedidoClinicoPapel, texto: str) -> None:
    d = ped.datos
    _encabezado(c, "RESEÑA CLÍNICA", d.numero)
    col2 = MARGEN_X + 92 * mm
    _campo(c, MARGEN_X, 38, "Paciente:", d.paciente, col2 - 2 * mm)
    _campo(c, col2, 38, "DNI:", d.dni, DERECHA_X)
    _campo(c, MARGEN_X, 50, "Obra Social:", d.obra_social, col2 - 2 * mm)
    _campo(c, col2, 50, "N°Afiliado:", d.afiliado, DERECHA_X)
    _campo(c, MARGEN_X, 62, "Diagnóstico:", d.diagnostico, DERECHA_X)

    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT, 11.5)
    etiqueta = "Estudios solicitados:"
    c.drawString(MARGEN_X, _y(74), etiqueta)
    estudios = ", ".join(n for _, n in ped.resena_examenes)
    c.setFillColor(COLOR_DATO)
    c.setFont(FONT_B, 10.5)
    ex = MARGEN_X + c.stringWidth(etiqueta, FONT, 11.5) + 2 * mm
    lineas_est = _partir_lineas(c, estudios, FONT_B, 10.5, DERECHA_X - ex)
    for i, txt in enumerate(lineas_est[:2]):
        c.drawString(ex, _y(74 + i * 5.5), txt)

    top_texto = 92.0
    leading = 7.2
    max_lineas = 22
    c.setFillColor(COLOR_TEXTO)
    c.setFont(FONT_B, 11.5)
    c.drawString(MARGEN_X, _y(top_texto - 6), "Reseña:")
    lineas = _partir_lineas(c, texto, FONT, 12.5, DERECHA_X - MARGEN_X)[:max_lineas]
    if lineas:
        c.setFillColor(COLOR_DATO)
        c.setFont(FONT, 12.5)
        for i, txt in enumerate(lineas):
            c.drawString(MARGEN_X, _y(top_texto + 2 + i * leading), txt)
        c.setFillColor(COLOR_TEXTO)
    else:
        for i in range(12):
            _linea_punteada(c, MARGEN_X, DERECHA_X, _y(top_texto + 4 + i * 9))

    _pie_firma(c, 268, "", d.fecha)
    c.setLineWidth(0.8)
    c.setStrokeColor(colors.black)
    firma_cx = MARGEN_X + 38 * mm
    c.line(firma_cx - 32 * mm, _y(268) + 5 * mm, firma_cx + 32 * mm, _y(268) + 5 * mm)


def _armar_slots(
    pedidos: list[PedidoClinicoPapel | PedidoMicroPapel], resenas: dict[int, str]
) -> list:
    """Formularios en orden de impresión; None = mitad de hoja vacía."""
    slots: list = []
    for ped in pedidos:
        if isinstance(ped, PedidoMicroPapel):
            slots.append(lambda c, p=ped: _dibujar_pedido_micro(c, p))
            continue
        slots.append(lambda c, p=ped: _dibujar_pedido_clinico(c, p))
        if ped.resena_examenes:
            if ped.solicitud_id in resenas:
                texto = resenas[ped.solicitud_id]
            else:
                texto = construir_resena_reglas(_contexto_resena(ped))
            slots.append(lambda c, p=ped, t=texto: _dibujar_resena(c, p, t))
        if ped.incluye_probnp:
            if len(slots) % PEDIDOS_POR_HOJA:
                slots.append(None)
            slots.append(lambda c, d=ped.datos: _dibujar_probnp_solicitud(c, d))
            slots.append(lambda c, d=ped.datos: _dibujar_probnp_justificacion(c, d))
    return slots


def generar_pedidos_papel_pdf_bytes(
    items: list[ItemImpresion], resenas: dict[int, str] | None = None
) -> tuple[bytes, int]:
    """
    PDF A4 apaisado con 2 formularios por hoja (cada uno a tamaño A5): pedido,
    reseña si corresponde y los 2 formularios de proBNP juntos en una misma hoja.
    ``resenas``: {solicitud_id: texto revisado}; si falta, se usa la plantilla.
    Devuelve (bytes, cantidad de pedidos).
    """
    objs = _cargar_objetos(items)
    pedidos = _pedidos_en_orden(objs)
    slots = _armar_slots(pedidos, resenas or {})
    buf = BytesIO()
    hoja_w, hoja_h = landscape(A4)
    escala = (hoja_w / PEDIDOS_POR_HOJA) / PAGE_W
    c = rl_canvas.Canvas(buf, pagesize=(hoja_w, hoja_h))
    c.setTitle("Pedidos de laboratorio")
    for i, dibujar in enumerate(slots):
        pos = i % PEDIDOS_POR_HOJA
        if pos == 0 and i > 0:
            c.showPage()
        if dibujar is None:
            continue
        nombre_form = f"pedido_{i}"
        c.beginForm(nombre_form, 0, 0, PAGE_W, PAGE_H)
        dibujar(c)
        c.endForm()
        c.saveState()
        c.translate(pos * hoja_w / PEDIDOS_POR_HOJA, hoja_h - PAGE_H * escala)
        c.scale(escala, escala)
        c.doForm(nombre_form)
        c.restoreState()
        if pos == 0 and i + 1 < len(slots) and slots[i + 1] is not None:
            _linea_corte(c, hoja_w / PEDIDOS_POR_HOJA, hoja_h)
    c.save()
    return buf.getvalue(), len(pedidos)


# ---------------------------------------------------------------------------
# Listado del día
# ---------------------------------------------------------------------------


def _estudios_texto_lab(sol: SolicitudExamen) -> str:
    ped = construir_pedido_clinico(sol, componentes_basicos=set())
    nombres = [
        lbl
        for lbl, _, cod in (*FORM_CLINICO_IZQ, *FORM_CLINICO_DER)
        if cod and cod in ped.marcados
    ]
    nombres.extend(ped.otros)
    return ", ".join(nombres) or "—"


def _estudios_texto_micro(est: EstudioMicrobiologia) -> str:
    partes = []
    if est.tipo_cultivo_id and est.tipo_cultivo:
        partes.append(est.tipo_cultivo.nombre or est.tipo_cultivo.codigo)
    elif (est.tipo_estudio or "").strip():
        partes.append(est.tipo_estudio.strip())
    if est.tipo_muestra_micro_id and est.tipo_muestra_micro:
        partes.append(f"Muestra: {est.tipo_muestra_micro.nombre}")
    return " · ".join(p for p in partes if p) or "—"


def _origen_extraccion_listado(obj: SolicitudExamen | EstudioMicrobiologia) -> str:
    """Lugar / procedencia de extracción para la columna Origen del listado."""
    if isinstance(obj, SolicitudExamen):
        from laboratorio.models_catalog import Muestra
        from laboratorio.services_etiqueta_muestra import (
            resolver_lugar_etiqueta_desde_solicitud,
        )

        for lugar in (
            Muestra.objects.filter(solicitud_id=obj.pk)
            .exclude(lugar_extraccion__isnull=True)
            .exclude(lugar_extraccion="")
            .values_list("lugar_extraccion", flat=True)[:1]
        ):
            if (lugar or "").strip():
                return lugar.strip()
        return resolver_lugar_etiqueta_desde_solicitud(obj) or "—"

    from laboratorio.services_etiqueta_microbiologia import resolver_lugar_etiqueta_estudio

    return (resolver_lugar_etiqueta_estudio(obj) or "").strip() or "—"


def generar_listado_ordenes_dia_pdf_bytes(
    items: list[ItemImpresion], fecha_label: str = ""
) -> tuple[bytes, int]:
    objs = _cargar_objetos(items)
    buf = BytesIO()
    page = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=24 * mm,
        bottomMargin=12 * mm,
        title="Órdenes del día",
    )
    st_h = ParagraphStyle("h", fontName=FONT_B, fontSize=8, leading=10, textColor=colors.white)
    st_c = ParagraphStyle("c", fontName=FONT, fontSize=8, leading=10)
    st_cb = ParagraphStyle("cb", parent=st_c, fontName=FONT_B)

    def P(text: str, style=st_c) -> Paragraph:
        t = (text or "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(t, style)

    header = [
        P("Pedido", st_h), P("Paciente", st_h),
        P("DNI", st_h), P("Obra social", st_h), P("Origen", st_h), P("Médico", st_h),
        P("Estudios solicitados", st_h),
    ]
    rows = [header]
    for idx, obj in enumerate(objs, start=1):
        nombre, dni = _fmt_paciente(obj.paciente)
        os_txt = (getattr(obj.paciente, "obra_social", None) or "").strip()
        afil = (getattr(obj.paciente, "numero_afiliado", None) or "").strip()
        if afil:
            os_txt = f"{os_txt} · {afil}" if os_txt else afil
        origen = _origen_extraccion_listado(obj)
        if isinstance(obj, SolicitudExamen):
            medico = _fmt_medico(obj.medico_interno, obj.medico_externo_nombre or "")
            estudios = _estudios_texto_lab(obj)
        else:
            medico = _fmt_medico(obj.medico_interno, obj.medico_externo_nombre or "")
            estudios = _estudios_texto_micro(obj)
        # Índice del día como ayuda visual delante del número (sin columna aparte).
        pedido_txt = f"{idx} · {obj.numero or f'#{obj.pk}'}"
        rows.append([
            P(pedido_txt, st_cb), P(nombre, st_cb),
            P(dni), P(os_txt or "—"), P(origen), P(medico), P(estudios),
        ])
    # Sin columna "#"; el índice va en Pedido. Origen antes de Médico (~277 mm).
    widths = [34, 48, 20, 34, 32, 36, 73]
    table = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A6E")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F5F9")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#C9CED8")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    generado = timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")
    titulo = "Órdenes del día" + (f" — {fecha_label}" if fecha_label else "")
    total = len(objs)

    def _decorar(cv: rl_canvas.Canvas, _doc) -> None:
        w, h = page
        cv.saveState()
        path = LABORATORIO_STATIC / (INFORME_LAB_CONFIG.get("logo") or "icpl_logo.png")
        if path.is_file():
            try:
                cv.drawImage(
                    ImageReader(str(path)), 10 * mm, h - 20 * mm, width=34 * mm,
                    height=14 * mm, preserveAspectRatio=True, anchor="w", mask="auto",
                )
            except Exception:
                pass
        cv.setFont(FONT_B, 13)
        cv.drawCentredString(w / 2, h - 12 * mm, titulo)
        cv.setFont(FONT, 8.5)
        cv.setFillColor(colors.HexColor("#555555"))
        cv.drawCentredString(w / 2, h - 17 * mm, f"{INFORME_LAB_CONFIG.get('titulo', '')} · {total} orden(es)")
        cv.drawString(10 * mm, 6 * mm, f"Generado: {generado}")
        cv.drawRightString(w - 10 * mm, 6 * mm, f"Página {cv.getPageNumber()}")
        cv.restoreState()

    doc.build([Spacer(1, 1 * mm), table], onFirstPage=_decorar, onLaterPages=_decorar)
    return buf.getvalue(), total


def auditar_impresion_ordenes(
    *, actor, accion: str, items: Iterable[ItemImpresion], view: str, extra: dict | None = None
) -> None:
    items = list(items)
    log_event(
        action="UPDATE",
        actor=actor,
        entity_type="laboratorio.ImpresionOrdenes",
        entity_repr="laboratorio.ImpresionOrdenes",
        after=None,
        module="laboratorio",
        metadata={
            "accion": accion,
            "solicitud_ids": [i.id for i in items if i.tipo == TIPO_LAB],
            "estudio_micro_ids": [i.id for i in items if i.tipo == TIPO_MICRO],
            "view": view,
            **(extra or {}),
        },
    )
